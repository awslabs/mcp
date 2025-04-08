import streamlit as st
from netmiko import ConnectHandler

# Título da aplicação
st.title("Gerenciador de VLANs para Switches Huawei")

# Sidebar para conexão ao switch
st.sidebar.header("Configurações de Conexão")
switch_ip = st.sidebar.text_input("IP do Switch")
usuario = st.sidebar.text_input("Usuário")
senha = st.sidebar.text_input("Senha", type="password")
interface = st.sidebar.text_input("Interface (ex: GigabitEthernet0/0/1)", value="GigabitEthernet0/0/1")

# Função para conectar ao switch
def conectar_switch(ip, usuario, senha):
    try:
        dispositivo = {
            'device_type': 'huawei',
            'host': ip,
            'username': usuario,
            'password': senha,
        }
        conexao = ConnectHandler(**dispositivo)
        st.sidebar.success("Conectado ao switch com sucesso!")
        return conexao
    except Exception as e:
        st.sidebar.error(f"Erro ao conectar ao switch: {e}")
        return None

# Conectar ao switch
if st.sidebar.button("Conectar"):
    conexao = conectar_switch(switch_ip, usuario, senha)
else:
    conexao = None

# Função para criar VLAN
def criar_vlan(conexao, vlan_id, nome_vlan, ip, mascara, interface):
    try:
        comandos = [
            f"vlan {vlan_id}",
            f"description {nome_vlan}",
            f"interface {interface}",
            f"port link-type access",
            f"port default vlan {vlan_id}",
            f"interface Vlanif{vlan_id}",
            f"ip address {ip} {mascara}",
            "quit",
        ]
        conexao.send_config_set(comandos)
        st.success(f"VLAN {vlan_id} criada e configurada com sucesso!")
    except Exception as e:
        st.error(f"Erro ao criar VLAN: {e}")

# Função para excluir VLAN
def excluir_vlan(conexao, vlan_id, interface):
    try:
        comandos = [
            f"undo vlan {vlan_id}",
            f"interface {interface}",
            "undo port default vlan",
            "quit",
        ]
        conexao.send_config_set(comandos)
        st.success(f"VLAN {vlan_id} excluída com sucesso!")
    except Exception as e:
        st.error(f"Erro ao excluir VLAN: {e}")

# Seção para criar VLAN
st.header("Criar VLAN")
vlan_id_criar = st.text_input("ID da VLAN (criar)")
nome_vlan = st.text_input("Nome da VLAN")
ip_vlan = st.text_input("Endereço IP (ex: 192.168.1.1)")
mascara_vlan = st.text_input("Máscara de rede (ex: 255.255.255.0)")

if st.button("Criar VLAN"):
    if conexao:
        criar_vlan(conexao, vlan_id_criar, nome_vlan, ip_vlan, mascara_vlan, interface)
    else:
        st.error("Conecte-se ao switch primeiro.")

# Seção para excluir VLAN
st.header("Excluir VLAN")
vlan_id_excluir = st.text_input("ID da VLAN (excluir)")

if st.button("Excluir VLAN"):
    if conexao:
        excluir_vlan(conexao, vlan_id_excluir, interface)
    else:
        st.error("Conecte-se ao switch primeiro.")