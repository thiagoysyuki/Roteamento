import streamlit as st
import pandas as pd
import seaborn
import numpy as np
from pulp import *
import re
import datetime as dt

tabela_custos = pd.read_excel("Dados/Rotas.xlsx",sheet_name="custo_hora")
tabela_custos.set_index('Unidade', inplace=True)

## Seleção de variáveis

st.title("Otimizador de Rotas")

unidades = tabela_custos.columns

escolhas = st.multiselect("Selecione as Unidades da Rota",unidades)

custo = tabela_custos.loc[escolhas,escolhas]

custo_matriz= np.matrix(custo)

st.subheader("Tabela dos custos - Horas")
tabela_custo = st.table(custo)

## Otimização

n = len(custo)

arcos = [(i,j) for i in range(n) for j in range(n) if custo_matriz[i,j] != 999]

tsp = LpProblem("RoteiroMalote", sense= LpMinimize)

x = LpVariable.dicts("Trajeto",arcos, cat="Binary")
print(x)

u = LpVariable.dicts("loja", [i for i in range(n)], lowBound=1, upBound=n, cat="Continuous")
print(u)

tsp += lpSum([custo_matriz[i,j] * x[i,j] for (i,j) in arcos])
print(tsp)


for j in range(n):
    tsp += lpSum([x[i,j] for (i,m) in arcos if m==j]) == 1


print(tsp)

for i in range(n):
    tsp += lpSum([x[i,j] for (m,j) in arcos if m == i]) == 1


for i in range(n):
    tsp += lpSum([x[i,j] for (m,j) in arcos if m == i]) == 1


for (i,j) in arcos:
    if i > 0 and i != j:
        tsp += u[i] - u[j] + n * x[i,j] <= n-1

resolver_modelo = tsp.solve()


resultados = []
variaveis = []
for var in tsp.variables():
    if var.varValue > 0:
        variaveis.append(var.name)
        resultados.append(var.varValue)


tabela_rotas_ordem = pd.DataFrame({"Variaveis": variaveis, "Sequencia": resultados})

## Tabela Ordem

tabela_ordem = tabela_rotas_ordem[tabela_rotas_ordem['Variaveis'].str.contains("loja")]
tabela_ordem["Sequencia"] = tabela_ordem["Sequencia"].astype('int32')

def extrair_loja(text):
   return re.findall(r'\d+', text)[-1]

def definir_loja(id):
    return escolhas[id]

retorn_var = tabela_ordem.iloc[0]["Variaveis"]
retorn_seq = tabela_ordem["Sequencia"].min() - 1


retorno = pd.DataFrame([{"Variaveis": retorn_var, "Sequencia": str(retorn_seq)}])

tabela_ordem = pd.concat([tabela_ordem,retorno])


tabela_ordem['id_loja'] = tabela_ordem['Variaveis'].apply(extrair_loja)
tabela_ordem['id_loja'] = tabela_ordem['id_loja'].astype("int32")
tabela_ordem['Loja'] = tabela_ordem["id_loja"].apply(definir_loja)
tabela_ordem['Sequencia'] = tabela_ordem['Sequencia'].astype("int32")

## Tabela Rotas

tabela_rotas = tabela_rotas_ordem[tabela_rotas_ordem['Variaveis'].str.contains("Trajeto")]


def extrair_rota_dest(text):
   dest_id = int(re.findall(r'\d+', text)[-1])
   dest_nome = escolhas[dest_id]
   return dest_nome

def extrair_rota_orig(text):
   orig_id = int(re.findall(r'\d+', text)[0])
   orig_nome = escolhas[orig_id]
   return orig_nome


tabela_rotas['origem'] = tabela_rotas['Variaveis'].apply(extrair_rota_orig)
tabela_rotas['destino'] = tabela_rotas['Variaveis'].apply(extrair_rota_dest)

## Resutado

st.write(f"Tempo total em Horas sem transbordo = {round(value(tsp.objective),2)}")
st.write(f"Status da otimização:", LpStatus[resolver_modelo]) 

st.subheader("Roteiro")

st.write(f"Ponto de saída: {escolhas[0]}")
st.table(tabela_ordem[["Sequencia", "Loja"]].sort_values("Sequencia"))


st.subheader("Itinerário")

hr_saida = st.time_input("Hora de Saída", dt.time(8, 30))
transbordo = st.time_input("Tempo médio de transbordo", dt.time(0, 30))

origem = []
destino = []
custo_traj = []

for i in range(tabela_ordem.shape[0]-1):
    entr = tabela_ordem.iloc[i]['Loja']
    said = tabela_ordem.iloc[i+1]['Loja']
    cust = custo.loc[entr][said]
    origem.append(entr)
    destino.append(said)
    custo_traj.append(cust)
    

    
itinerarios = pd.DataFrame({"Origem": origem, "Destino": destino, "Custo" : custo_traj})



def acumular():
    afericao = []
    transb =  transbordo.minute/60 + transbordo.hour  
    for i in range(itinerarios.shape[0]):
        if i == 0:
            afericao.append(itinerarios.iloc[i]['Custo'])  
        else:
            acumulador = itinerarios.iloc[i]['Custo'] + afericao[i-1] + transb
            afericao.append(acumulador)
    return afericao

acumulado = acumular()

itinerarios.insert(column="Acum", value=acumulado, loc=3)

hrs_saida_dc = hr_saida.hour + hr_saida.minute/60 



itinerarios["Horarios_dec"] = itinerarios['Acum'] + hrs_saida_dc


def converter_horario(time):
    hours = int(time)
    minutes = int((time*60) % 60)
    return f"{hours:02d}:{minutes:02d}"

itinerarios["Horarios"] = itinerarios["Horarios_dec"].apply(converter_horario)

st.table(itinerarios[["Origem","Destino","Horarios","Acum"]])

st.subheader(f"Horario de retorno >  {itinerarios.loc[max(itinerarios.index)]["Horarios"]}")

