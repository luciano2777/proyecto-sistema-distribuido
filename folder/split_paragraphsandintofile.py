path = r"/home/luciano/Desktop/Universidad/12 trimesre/sistema distribuido/Proyecto/branchLuciano/test.txt"
import os
import json
def file_to_paragraphs(path):
    with open(path, 'r', encoding='utf-8') as file:
        
        paragraphs = file.read().strip().split('\n\n')
    return paragraphs

def paragraphs_into_json(id, text):
    # 1. Get the directory where THIS script is saved
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Construct the full path
    filename = f"{id}.json"
    file_path = os.path.join(script_dir, filename)

    data = {
        "id": id,
        "text": text 
    }

    # 3. Write to the specific file_path
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

    # 4. Only print the real path once
    print(f"JSON file saved to: {file_path}")

def automatic_split(path, dir, clients): #clients es una lista de los usuarios conectados.
    list=file_to_paragraphs(path)

    Lenclients = len(clients)
    distribution = [[] for _ in range(Lenclients)]

    temp_list = list.copy() 

    current_client = 0
    while temp_list:
        paragraph = temp_list.pop(0)
        
        distribution[current_client].append(paragraph)
        
        current_client = (current_client + 1) % Lenclients

    for id_client, paragraphs in enumerate(distribution):
        if paragraphs:
            paragraphs_into_json(id_client, paragraphs) # tras esto el software creará una lista de diccionarios.
    pass

def parragraph_into_dictlist(path, dir, clients): #clients es una lista de los usuarios conectados.
    list=file_to_paragraphs(path)

    Lenclients = len(clients)
    distribution = [[] for _ in range(Lenclients)]

    temp_list = list.copy() 

    current_client = 0
    while temp_list:
        paragraph = temp_list.pop(0)
        
        distribution[current_client].append(paragraph)
        
        current_client = (current_client + 1) % Lenclients
    listdict = []
    for id_client, paragraphs in enumerate(distribution):
        if paragraphs:
            data = {
        "id": id_client,
        "text": paragraphs 
    }       
            listdict.append(data)
    pass
    return listdict
list=file_to_paragraphs(path)
print(f"the path is a {list} which is {len(list)}")

clients = 20
distribution = [[] for _ in range(clients)]

temp_list = list.copy() 

current_client = 0
while temp_list:
    paragraph = temp_list.pop(0)
    
    distribution[current_client].append(paragraph)
    
    current_client = (current_client + 1) % clients

for id_client, paragraphs in enumerate(distribution):
    if paragraphs:
        paragraphs_into_json(id_client, paragraphs)