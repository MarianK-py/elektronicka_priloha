#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import yaml
import re


# In[2]:


pacienti = pd.read_excel("Vysledky system.xlsx", sheet_name='Hárok1')
pacienti.set_index("Rodné číslo", inplace=True) 
pacienti["Olumiant"] = pacienti["Olumiant"].map({"ano":1, "áno":1, 0:0, 1:1})
pacienti["BMI"] = (pacienti["váha"]/((pacienti["výška"]/100)**2)).round(1)
#pacienti["dátum prijatia"] = pacienti["dátum prijatia"].dt.strftime('%d.%m.%Y')
pacienti["dátum prijatia"] = pd.to_datetime(pacienti["dátum prijatia"], format='%d.%m.%Y')
#pacienti["datum prepustenia"] = pacienti["datum prepustenia"].dt.strftime('%d.%m.%Y')
pacienti["datum prepustenia"] = pd.to_datetime(pacienti["datum prepustenia"], format='%d.%m.%Y')


# Zoznamy a slovníky pre vyhľadávanie v texte

# In[3]:


udaje = {"oxygenoterapia": ["Oxygenoterap", "oxygenoterap",
                            "HFNO", "high-flow", "high flow", "low-flow", "low flow",
                            "UPV", "umel.{1,5}pľúc.{1,5}venti.{8}", "CPAP",
                            "maska", "nosová kanyla"],
         "smrť": ["exitus", "exit.{11}", "lethalis", "leth.{5}"], 
         "JIS": ["JIS", "jedno.{2,6}inten.{5,9}staro.{10}"]}

vys_vah = [["výška.{0,3}[0-9]+.{0,2}cm"], ["váha.{0,3}[0-9]+.{0,2}kg", "hmotnosť.{0,3}[0-9]+.{0,2}kg"],
           ["[0-9]+.{0,2}cm.{0,2}/.{0,2}[0-9]+.{0,2}kg"], ["[0-9]+.{0,2}cm,.{0,2}[0-9]+.{0,2}kg"], ["[0-9]+.{0,2}cm .{0,2}[0-9]+.{0,2}kg"],
           ["[0-9]+.{0,2}kg.{0,2}/.{0,2}[0-9]+.{0,2}cm"], ["[0-9]+.{0,2}kg,.{0,2}[0-9]+.{0,2}cm"], ["[0-9]+.{0,2}kg .{0,2}[0-9]+.{0,2}cm"]]

vys_vah_sep = [["", ["výška"]], ["", ["váha"]], 
               ["/", ["výška", "váha"]], [",", ["výška", "váha"]], ["cm", ["výška", "váha"]], 
               ["/", ["váha", "výška"]], [",", ["váha", "výška"]], ["kg", ["váha", "výška"]]]

vys_basic = ["[0-9]+.{0,2}cm"]

vah_basic = ["[0-9]+.{0,2}kg"]

saturacia = ["spo2", "sato2", "sat.o2"]

saturacia_doplnky = ["", "pri prijati", "bez kyslík", "pri prijati bez kyslík"]

poz = ["poz"]

neg = ["neg"]


# In[4]:


with open("informations.yml", "r", encoding='utf8') as f:
    inf = yaml.safe_load(f)

choroby = inf["choroby"]
vysledky = inf["vysledky"]
lieky = inf["lieky"]
protilatky = inf["protilatky"]
vyber = inf["vyberove"]


# Funkcia ktorá v z dataframu spravý text a zavolá vyhľadávacie funkcie

# In[5]:


def text_finder(pacient):
    hlavny_text = ""
    imuno_text = ""
    data = dict()
    data_temp = dict()
    problemy = []
    problemy_temp = []
    nenajdene = dict()
    
    start_imuno = False
    for index, value in pacient.iloc[:,0].items():
        if(value == "Imunologické vyš.:"):
            start_imuno = True
        if(type(value) !=  float):
            if start_imuno:
                imuno_text += str(value)+"\n"
            else:
                hlavny_text += str(value)+"\n"
    
    #Osobne udaje:
    if vyber["hlavicka"]:
        data_temp, problemy_temp = osobne_udaje(pacient)
        data.update(data_temp)
        problemy += problemy_temp
    
    if ("chýba správa" in hlavny_text):
        print(pacient.iloc[:,0][0])
        print("Chýba správa")
        print()
        return data, ["chýba správa"], []
    
    #Zakl. udaje:
    data_temp, problemy_temp = find_stav_pac(hlavny_text)
    data.update(data_temp)
    problemy += problemy_temp
    
    #Protilátky pri prijatí:
    for p in protilatky.values():
        data_temp, problemy_temp = find_protilatky(hlavny_text, p)
        data.update(data_temp)
        problemy += problemy_temp
    
    #Vyska/vaha:
    data_temp, problemy_temp = find_vys_vah(hlavny_text)
    data.update(data_temp)
    problemy += problemy_temp
    if (len(problemy_temp) == 0):
        BMI = round(data["váha"]/((data["výška"]/100)**2), 1)
        if (BMI > 60 or BMI < 10):
            problemy.append("BMI")
    
    #Saturacia:
    data_temp, problemy_temp = find_saturacia(hlavny_text)
    data.update(data_temp)
    problemy += problemy_temp 
        
    #Lieky:
    data_temp = find_lieky(hlavny_text)
    data.update(data_temp)
        
    #Vylsedky:  
    if (imuno_text != ""):
        data_temp, problemy_temp, nenajdene = find_vysledky(imuno_text, vysledky)
        if (len(nenajdene) != 0):
            data.update(data_temp)
            problemy += problemy_temp
            data_temp, problemy_temp, nenajdene = find_vysledky(hlavny_text, nenajdene)
    else:
        data_temp, problemy_temp, nenajdene = find_vysledky(hlavny_text, vysledky)
    data.update(data_temp)
    problemy += problemy_temp 
            
    #Choroby: 
    data_temp, problemy_temp = find_choroby(hlavny_text)
    data.update(data_temp)
    problemy += problemy_temp 
    
    print(pacient.iloc[:,0][0])
    print("Problematické údaje:",problemy)
    print("Nenajdene vysl.:",list(nenajdene.keys()))
    print()
    
    return data, problemy, list(nenajdene.keys())
    


# Funkcia hľadajúce udaje ako meno, RČ a dobu hospitalizácie 

# In[6]:


def osobne_udaje(pacient):
    data = dict()
    problemy = []

    data["Meno"] = pacient[pacient.columns[0]][0].strip()
    data["Rodné číslo"] = pacient[pacient.columns[1]][0].strip()
    found_pri = False
    try:
        data["dátum prijatia"] = pd.to_datetime(pacient[pacient.columns[2]][0], format="%d.%m.%Y")
        found_pri = True
    except:
        problemy.append("dátum prijatia")

    found_pre = False
    if (type(pacient[pacient.columns[3]][0]) is str):
        if ("preklad" in pacient[pacient.columns[3]][0]):
            try:
                data["datum prepustenia"] = pd.to_datetime(pacient[pacient.columns[4]][0], format="%d.%m.%Y")
                found_pre = True
            except:
                problemy.append("dátum prepustenia (preklad)")
        else:
            try:
                data["datum prepustenia"] = pd.to_datetime(pacient[pacient.columns[3]][0], format="%d.%m.%Y")
                found_pre = True
            except:
                problemy.append("dátum prepustenia (bez prekladu)")
    else:
        try:
            data["datum prepustenia"] = pd.to_datetime(pacient[pacient.columns[3]][0], format="%d.%m.%Y")
            found_pre = True
        except:
            problemy.append("dátum prepustenia (bez prekladu)")
    if vyber["doba_hospitalizacie"]:
        if found_pri and found_pre:
            data["dlžka hosp."] = (data["datum prepustenia"] - data["dátum prijatia"]).days
            if (data["dlžka hosp."] < 0 or data["dlžka hosp."] > 100):
                    problemy.append("dlzka hospitalizacie")

    if found_pri:
        rok_nar = int(data["Rodné číslo"][0:2])
        if (rok_nar < 22):
            if len(data["Rodné číslo"]) == 11:
                rok_nar += 100
        mes_nar = int(data["Rodné číslo"][2:4])
        if (mes_nar > 50):
            mes_nar -= 50
        den_nar = int(data["Rodné číslo"][4:6])

        vek = 0

        if (data["dátum prijatia"].month < mes_nar):
            vek = (data["dátum prijatia"].year - 1901) - rok_nar
        elif (data["dátum prijatia"].month > mes_nar):
            vek = (data["dátum prijatia"].year - 1900) - rok_nar
        else:
            if (data["dátum prijatia"].day < den_nar):
                vek = (data["dátum prijatia"].year - 1901) - rok_nar
            elif (data["dátum prijatia"].day >= den_nar):
                vek = (data["dátum prijatia"].year - 1900) - rok_nar

        if vyber["vek"]:
            if vek >= 0 and vek < 120:
                data["vek"] = vek
            else:
                problemy.append("vek")

        data["dátum prijatia"] = data["dátum prijatia"].strftime('%d.%m.%Y')

    if found_pre:
        data["datum prepustenia"] = data["datum prepustenia"].strftime('%d.%m.%Y')
    
    return data, problemy
    


# Hľadanie udajov o stave pacienta ako oxygenoterapia/JIS/smrť

# In[22]:


def find_stav_pac(text):
    data = dict()
    problemy = []
    for i, udaj in udaje.items():
        out = []
        for j in udaj:
            out += re.findall(j,text)
        if vyber[i]:
            if (i == "oxygenoterapia"):

                if (len(out) == 0):
                    data[i] = "bez oxygenoterapie"
                else:
                    if (("HFNO" in out) or ("high-flow" in out) or ("high flow" in out)):
                        if ("UPV" in out):
                            data[i] = "HFNO/UPV"
                        else:
                            data[i] = "HFNO"
                    elif ("UPV" in out):
                        data[i] = "UPV"
                    elif (("low-flow" in out) or ("low flow" in out)):
                        data[i] = "low-flow"
                    else:
                        data[i] = "low-flow (neupresnené)"
                        chyba = re.findall("bez oxygenoterap",text)
                        if len(chyba) > 0:
                            data[i] = ""
                            problemy.append("oxygenoterapia")
            else:
                if (len(out) == 0):
                    data[i] = 0
                else:
                    data[i] = 1
        
    return data, problemy


# Funkcia hľadajúca informácie o protilátkach

# In[8]:


def find_protilatky(text, ochorenie):
    out = []
    problemy = []
    data = dict()
    text = text.lower()
    protilatky = ochorenie["nazvy_protilatok"]
    stlpce = ochorenie["nazvy_stlpcov"]
    proti_dolezite = poz+neg+protilatky

    if len(protilatky) == 0:
        for n in ochorenie["nazvy_ochorenia"]:
            for vysl in (poz+neg):
                out += re.findall(n+".{0,40}"+vysl,text)

        if (out != []):
            for test in out:
                rozdel_test = re.split(",| |/|:|-|\(|\)|–",test)
                #print(rozdel_test)
                for i in rozdel_test.copy():
                    remove = True
                    for p in proti_dolezite:
                        if p in i:
                            remove = False
                    if remove or i == "":
                        rozdel_test.remove(i)

                for i in rozdel_test:
                    if neg[0] in i:
                        data[stlpce[0]] = 0
                    if poz[0] in i:
                        data[stlpce[0]] = data.get(stlpce[0], 1)*1

    elif len(protilatky) == 1:
        for n in ochorenie["nazvy_ochorenia"]:
            for vysl in (poz+neg):
                out += re.findall(n+".{0,40}"+protilatky[0]+".{0,10}"+vysl,text)

        if (out != []):
            for test in out:
                rozdel_test = re.split(",| |/|:|-|\(|\)|–",test)
                #print(rozdel_test)
                for i in rozdel_test.copy():
                    remove = True
                    for p in proti_dolezite:
                        if p in i:
                            remove = False
                    if remove or i == "":
                        rozdel_test.remove(i)

                for i in rozdel_test:
                    if neg[0] in i:
                        data[stlpce[0]] = 0
                    if poz[0] in i:
                        data[stlpce[0]] = data.get(stlpce[0], 1)*1

        for i in stlpce:
            if i not in data:
                problemy.append(i)

    else:
        for n in ochorenie["nazvy_ochorenia"]:
            for vysl in (poz+neg):
                out += re.findall(n+".{0,40}"+protilatky[0]+".{0,30}"+protilatky[1]+".{0,10}"+vysl,text)
                out += re.findall(n+".{0,40}"+protilatky[1]+".{0,30}"+protilatky[0]+".{0,10}"+vysl,text)

            out += re.findall(n+".{0,40}"+protilatky[1]+".{0,30}"+protilatky[0]+".{0,20}",text)
            out += re.findall(n+".{0,40}"+protilatky[0]+".{0,30}"+protilatky[1]+".{0,20}",text)

        if (out != []):
            for test in out:
                rozdel_test = re.split(",| |/|:|-|\(|\)|–",test)
                #print(rozdel_test)
                for i in rozdel_test.copy():
                    remove = True
                    for p in proti_dolezite:
                        if p in i:
                            remove = False
                    if remove or i == "":
                        rozdel_test.remove(i)


                #print(rozdel_test)

                IgM, IgG = pozicie_testov(rozdel_test, protilatky)

                counter = 0
                while (IgM != -1 and IgG != -1 and counter < 5):
                    vysl = vysledky_testov(IgM, IgG, rozdel_test)
                    if (vysl[0] != -1):
                        data[stlpce[1]] = data.get(stlpce[1], 1) * vysl[0]
                    if (vysl[1] != -1):
                        data[stlpce[0]] = data.get(stlpce[0], 1) * vysl[0]
                    rozdel_test = rozdel_test[(max(IgM, IgG))+1:]
                    IgM, IgG = pozicie_testov(rozdel_test, protilatky)
                    counter += 1
        for i in stlpce:
            if i not in data:
                problemy.append(i)

        #print(data)
    return data, problemy


# Zisťovanie pozitivity/negativity 

# In[9]:


def poz_alebo_neg(vysl):
    pozit = []
    negat = []
    
    if vysl.isdigit():
        return 1
    
    for p in poz:
        pozit += re.findall(p, vysl)
    for n in neg:
        negat += re.findall(n, vysl)

    if (pozit == [] and negat == []) or (pozit != [] and negat != []):
        return -1
    elif pozit != []:
        return 1
    else:
        return 0


# In[10]:


def pozicie_testov(rozdel_test, proti):
    IgM = -1
    if (proti[1] in rozdel_test):
        IgM = rozdel_test.index(proti[1])
    else:
        for j, cast in enumerate(rozdel_test):
            if proti[1] in cast:
                IgM = j
                
    IgG = -1
    if (proti[0] in rozdel_test):
        IgG = rozdel_test.index(proti[0])
    else:
        for j, cast in enumerate(rozdel_test):
            if proti[0] in cast:
                IgG = j
                
    return [IgM, IgG]


# Hľadanie výseldkov jendého protilátkového testu

# In[11]:


def vysledky_testov(IgM, IgG, rozdel_test):
    pocet_casti = len(rozdel_test)
    vysl = [-1, -1]
    swap = False
    if (IgM > IgG):
        swap = True
        IgM, IgG = IgG, IgM
        
    if (IgM > 0):
        pozitM1 = poz_alebo_neg(rozdel_test[IgM-1])
    else:
        pozitM1 = -1
    if (IgM+1 < pocet_casti):
        pozitM2 = poz_alebo_neg(rozdel_test[IgM+1])
    else:
        pozitM2 = -1
                    
    if (IgG > 0):
        pozitG1 = poz_alebo_neg(rozdel_test[IgG-1])
    else:
        pozitG1 = -1
    if (IgG+1 < pocet_casti):
        pozitG2 = poz_alebo_neg(rozdel_test[IgG+1])
    else:
        pozitG2 = -1


    if (pozitM1 != -1):
        vysl[0] = pozitM1
    elif (pozitM2 != -1):
        vysl[0] = pozitM2
    elif (IgM+1 == IgG):
        if (pozitG2 != -1):
            vysl[0] = pozitG2

    if (pozitG2 != -1):
        vysl[1] = pozitG2
    elif (pozitG1 != -1):
        vysl[1] = pozitG1
    elif (IgM+1 == IgG):
        if (pozitM1 != -1):
            vysl[1] = pozitM1

    if (pozitM1 == -1 and pozitG2 == -1 and IgG != -1 and IgM != -1):
        vysl = [-1, -1]

    if (pozitM1 != -1 and pozitM2 != -1 and IgG == -1 ):
        vysl[0] = -1

    if (pozitG1 != -1 and pozitG2 != -1 and IgM == -1):
        vysl[1] = -1

    if swap:
        vysl.reverse()
        
    return vysl
            


# Hľadanie výšky/váhy

# In[12]:


def find_vys_vah(text):
    data = dict()
    problemy = []
    for i, hod in enumerate(vys_vah):
        out = []
        for j in hod:
            out += re.findall(j,text)
        if (out != []):
            for k in out:
                if vys_vah_sep[i][0] != "":
                    separated = k.split(vys_vah_sep[i][0])
                else:
                    separated = [k]
                for l, sep in enumerate(separated):
                    #print(vys_vah_sep[i][1][l],re.findall("[0-9]+",sep)[0])
                    data[vys_vah_sep[i][1][l]] = int(re.findall("[0-9]+",sep)[0])
                    if (vys_vah_sep[i][1][l] == "výška" and
                            (data["výška"] > 250 or data["výška"] < 20)):
                        problemy.append("výška")
                    elif (vys_vah_sep[i][1][l] == "váha" and
                            (data["váha"] > 300 or data["váha"] < 10)):
                        problemy.append("váha")
    if ("výška" not in data):
        problemy.append("výška")
    if ("váha" not in data):
        problemy.append("váha")
        
    return data, problemy


# Hľadanie saturácie

# In[13]:


def find_saturacia(text):
    data = dict()
    problemy = []
    text = text.lower()
    
    hodnoty_text = []
    hodnoty_cisla = []
    
    for sat in saturacia:
        for dop in saturacia_doplnky:
            if dop == "":
                hodnoty_text += re.findall(sat+".{1,3}[0-9]+",text)
            else:
                hodnoty_text += re.findall(sat+".{1,3}"+dop+".{1,3}[0-9]+",text)
        
    for hod in hodnoty_text:
        hod_cislo = int(re.findall("[0-9]+", hod)[-1])
        if (hod_cislo != 0 and hod_cislo <= 100):
            hodnoty_cisla.append(hod_cislo)
    
    if (len(hodnoty_cisla) != 0):
        data["SpO2 pri prijati bez kyslika"] = hodnoty_cisla[0]
    else:
        problemy.append("SpO2 pri prijati bez kyslika")
        
    return data, problemy


# Hľadanie liekov

# In[14]:


def find_lieky(text):
    text = text.lower()
    data = dict()
    for i, liekMena in lieky.items():
        out = []
        for liek in liekMena:
            out += re.findall(liek,text)
        if (len(out) == 0):
            #print(i,"= 0")
            data[i] = 0
        else:
            #print(i,"= 1")
            data[i] = 1
    return data


# Hľadanie vysledkov krvných testov

# In[15]:


def find_vysledky(text, vysledky_input):
    data = dict()
    problemy = []
    nenajdene = dict()
    for i, vysl in vysledky_input.items():
        hodnoty_text = []
        hodnoty_cisla = []
        
        for j in vysl:
            hodnoty_text += re.findall(j+".{1,3}[0-9,]+",text)
            
        for hod in hodnoty_text:
            hod_cislo = re.findall("[0-9,]+", hod)[-1].replace(",",".")
            if (hod_cislo != "."):
                if (hod_cislo[-1] == "."):
                    if (hod_cislo[0:-1].count(".") > 1):
                        problemy.append(i)
                    else:
                        hodnoty_cisla.append(float(hod_cislo[0:-1]))
                else:
                    if (hod_cislo.count(".") > 1):
                        problemy.append(i)
                    else:
                        hodnoty_cisla.append(float(hod_cislo))
                        
        if (len(hodnoty_cisla) == 0):
            nenajdene[i] = vysl
        elif (len(hodnoty_cisla) == 1):
            data[i] = hodnoty_cisla[0]
            #print(i,"=",hodnoty_cisla[0])
        else:
            prva_hod = hodnoty_cisla[0]
            for hod in hodnoty_cisla:
                if (prva_hod != hod):
                    if (i not in problemy):
                            problemy.append(i)
                else:
                    prva_hod = hod          
            data[i] = prva_hod
        
    return data, problemy, nenajdene


# Hľadanie chorôb u pacienta

# In[16]:


def find_choroby(text):
    data = dict()
    problemy = []
    for i, chor in choroby.items():
        out = []
        for j in chor:
            out += re.findall(j,text)
        if (len(out) == 0):
            #print(i,"= 0")
            data[i] = 0
        if (out != []):
            if (i == "CDI pri hosp"):
                vysl = kolitida_kontrola(text)
                if (vysl != -1):
                    data[i] = vysl
                else:
                    problemy.append("CDI pri hosp")
                #print(i, "problem")
            else:
                #print(i,"= 1",out)
                data[i] = 1
    return data, problemy


# Špeciálna kontrola pri kolitide

# In[17]:


def kolitida_kontrola(text):
    pozit = []
    negat = []
    for chor in choroby["CDI pri hosp"]:
        for p in poz:
            pozit += re.findall(chor+".{0,20}"+p, text)
        for n in neg:
            negat += re.findall(chor+".{0,20}"+n, text)
    
    if ((pozit == [] and negat == []) or (pozit != [] and negat != [])):
        return -1
    elif (pozit != []):
        return 1
    else:
        return 0


# Pridávanie dových výsledkov do hlavného dataframu (vypisovanie problémov) (vstup čísla harkov)

# In[18]:


def pridavanie_udajov(citany_subor, zapisovaci_subor,a, b):
    pacienti = pd.read_excel(zapisovaci_subor, sheet_name='Hárok1')
    pacienti.set_index("Rodné číslo", inplace=True) 
    if ("Deaxmetazon" in pacienti.columns):
        pacienti.rename(columns = {'Deaxmetazon':'Dexametazon'}, inplace = True)
    
    data = dict()
    problemy = []
    nenajdene = []
    with open("problemy "+citany_subor+".txt", "w", encoding='utf8') as problemy_dokument: 
        for p in range(a, b+1):
            print(f"Pacient z hárku {p}")
            try:
                pacient = pd.read_excel(citany_subor, sheet_name=f"Hárok{p}")
                if (len(pacient) == 0 or len(pacient) == 1):
                    print(f"Problém s hárkom {p}")
                    print()
                    continue
            except:
                print(f"Problém s hárkom {p}")
                print()
                continue
            data, problemy, nenajdene = text_finder(pacient)
            problemy_dokument.write(f"Pacient z hárku {p}:\n")
            problemy_dokument.write(f"Meno pacienta: {pacient.iloc[:,0][0]}\n")
            if ("chýba správa" in problemy):
                problemy_dokument.write(f"Chýba správa\n")
            else:
                problemy_dokument.write(f"Problemove udaje: {problemy}\n")
                problemy_dokument.write(f"Nenajdene vysledky: {nenajdene}\n")
            problemy_dokument.write("\n")
            if data != None:
                RC = data.pop("Rodné číslo")
                if (RC in pacienti.index):
                    print("Problém s menom:",data["Meno"],pacienti.loc[RC,"Meno"])
                    if data["Meno"] != pacienti.loc[RC,"Meno"]:
                        print("Problém s menom:",data["Meno"],pacienti.loc[RC,"Meno"])
                    for i, hod in data.items():
                        pacienti.loc[RC,i] = hod
                else:
                    pacienti.loc[RC] = data
    
    pacienti.reset_index(inplace=True)
    
    cols = list(pacienti.columns)
    a, b = cols.index('Meno'), cols.index('Rodné číslo')
    cols[b], cols[a] = cols[a], cols[b]
    pacienti = pacienti[cols]
    
    
    pacienti["Olumiant"] = pacienti["Olumiant"].map({"ano":1, "áno":1, 0:0, 1:1})
    pacienti["BMI"] = (pacienti["váha"]/((pacienti["výška"]/100)**2)).round(1)
    #pacienti["dátum prijatia"] = pacienti["dátum prijatia"].dt.strftime('%d.%m.%Y')
    #pacienti["datum prepustenia"] = pacienti["datum prepustenia"].dt.strftime('%d.%m.%Y')
    if "Unnamed: 26" in pacienti:
        del pacienti["Unnamed: 26"]
    if "dni" in pacienti:
        del pacienti["dni"]
    for i in re.findall("Dexametazon\.[0-9]+", str(pacienti.columns)):
        del pacienti[i]
    
    pacienti.to_excel(zapisovaci_subor, sheet_name="Hárok1",index = False)


# In[19]:


from time import perf_counter


# In[20]:


#pridavanie_udajov("Antivirotika KIGM COVID-19.xlsx", "Antivirotika KIGM COVID-19 doplnene.xlsx",2, 384)
#pridavanie_udajov("Antivirotika 2 KIGM COVID-19.xlsx", "Antivirotika KIGM COVID-19 doplnene.xlsx",1, 107)
#pridavanie_udajov("Antivirotika 2 KIGM COVID-19.xlsx", "Antivirotika KIGM COVID-19 doplnene special_2.xlsx",1, 107)
t = 0
for i in range(10):
    s = perf_counter()
    #pridavanie_udajov("Pacienti.xlsx", "Vysledky system.xlsx", 1, 101)
    e = perf_counter()
    print(e-s)
    t += e-s
print(t/10)


# In[23]:


pridavanie_udajov("Pacienti.xlsx", "Vysledky system.xlsx", 1, 101)


# In[ ]:


pacient = pd.read_excel("Pacienti.xlsx", sheet_name=f"Hárok{2}")

hlavny_text = ""
imuno_text = ""
data = dict()
data_temp = dict()
problemy = []
problemy_temp = []
nenajdene = dict()

start_imuno = False
for index, value in pacient.iloc[:,0].items():
    if(value == "Imunologické vyš.:"):
        start_imuno = True
    if(type(value) !=  float):
        if start_imuno:
            imuno_text += str(value)+"\n"
        else:
            hlavny_text += str(value)+"\n"


# In[ ]:


find_choroby(hlavny_text)


# In[ ]:


re.findall('hypertenz',hlavny_text)

