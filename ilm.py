import re
import requests
import pandas as pd
import folium
import webbrowser
import os

def andmed_veebist_faili():
    """
    Veebist andmete hankimine, millel põhineb ülejäänud programmi töö.
    Decode-encode ISO-8859-1 -> utf-8 on vajalik, et eesti täpitähti
    korrektselt kuvada. Andmed kirjutan xml-faili.
    """
    paring = requests.get('http://www.ilmateenistus.ee/ilma_andmed/xml/forecast.php')
    paring = paring.content.decode("ISO-8859-1")
    with open('andmed.xml', 'w', encoding='utf-8') as fail:
        fail.write(paring)

def andmed_failist_listi(failinimi):
    """
    Loen andmed failist programmi sisse ja panen iga rea eraldi listi liikmeks.
    """
    with open(failinimi) as f:
        andmed = f.readlines()
        ridade_list = []
        for rida in andmed:
            rida = rida.strip().split('\n')
            ridade_list.append(rida)
    return ridade_list

def andmed_stringiks(ridade_list):
    """
    Pesastatud listi lammutamine ning sõne moodustamine.
    """
    tasane_list = [y for x in ridade_list for y in x]
    sone = ''
    for element in tasane_list:
        sone += str(element)
    return sone

def dayAndmed(tekst_andmed):
    """
    Regulaaravaldis, mille eesmärgiks on eraldada <day> tagi vahele
    jääv osa tekstist.
    """
    dayRegex = re.compile(r'(<day>)(.*?)(</day>)')
    mo = dayRegex.search(tekst_andmed)
    return mo.group(0)

def placeRegex(tekst_andmed):
    """
    Regulaaravaldis, mille eesmärgiks on eraldada <place> tagi vahele
    jääv osa tekstist.
    """
    asukohaRegex = re.compile(r'(<place>)(.*?)(</place>)')
    return asukohaRegex.findall(str(tekst_andmed))

def nameRegex(placeRegex_andmed):
    """
    Regulaaravaldis, mille eesmärgiks on eraldada <name> tagi vahele
    jääv osa tekstist.
    """
    nimeRegex = re.compile(r'(<name>)(.*?)(</name>)')
    mo = nimeRegex.search(placeRegex_andmed)
    return mo.group(2)

def phenomenonRegex(placeRegex_andmed):
    """
    Regulaaravaldis, mille eesmärgiks on eraldada <phenomenon> tagi vahele
    jääv osa tekstist.
    """
    fenomRegex = re.compile(r'(<phenomenon>)(.*?)(</phenomenon>)')
    mo = fenomRegex.search(placeRegex_andmed)
    return mo.group(2)

def tempRegex(placeRegex_andmed):
    """
    Regulaaravaldis, mille eesmärgiks on eraldada <tempmax> tagi vahele
    jääv osa tekstist.
    """
    temperatRegex = re.compile(r'(<tempmax>)(.*?)(</tempmax>)')
    mo = temperatRegex.search(placeRegex_andmed)
    return mo.group(2)

def andmed_listidesse():
    """
    Funktsioon koondab kokku senise töö tulemused. Kutsub välja varem defineeritud
    funktsioone ja tagastab listid kohtade, ilmainfo ja õhutemperatuuri kohta.
    """
    andmed_veebist_faili()
    failinimi = 'andmed.xml'
    andmed = andmed_failist_listi(failinimi)
    tekst_andmed = andmed_stringiks(andmed)
    paeva_andmed = dayAndmed(tekst_andmed)
    kohad_ja_andmed = placeRegex(paeva_andmed)

    kohad, fenomenid, temperatuurid = [], [], []
    for koht in kohad_ja_andmed:
        uus_koht = nameRegex(str(koht))
        fenomen = phenomenonRegex(str(koht))
        temperatuur = tempRegex(str(koht))
        kohad.append(uus_koht)
        fenomenid.append(fenomen)
        temperatuurid.append(temperatuur)
    return (kohad, fenomenid, temperatuurid)

def andmefreim():
    """
    Koostan andmefreimi, mis koondab info kokku ühte tabelisse.
    """
    ilma_df = pd.DataFrame(
        {'kohad': andmed_listidesse()[0],
         'fenomenid': andmed_listidesse()[1],
         'temperatuurid': andmed_listidesse()[2]
        })
    return ilma_df

def koordinaadid():
    """
    Ilmajaamade geograafilised koordinaadid, et neid saaks hiljem kaardil kuvada.
    """
    koordinaatide_df = pd.DataFrame(
        {'kohad_koord': ['Harku', 'Jõhvi', 'Tartu', 'Pärnu', 'Kuressaare', 'Türi'],
         'laiuskraadid': [59.398056, 59.328889, 58.264167, 58.419722, 58.218056, 58.808611],
         'pikkuskraadid': [24.602778, 27.398333, 26.461389, 24.469722, 22.506389, 25.409167]
        })
    return koordinaatide_df

def andmetabel():
    """
    Liidan andmefreimile koordinaadid ja kustutan kohtade info, sest see on
    tarbetult kahekordselt.
    """
    suur_df = pd.concat([andmefreim(), koordinaadid()], axis=1)
    suur_df = suur_df.drop(['kohad_koord'], axis=1)
    return suur_df

def inglise_eesti():
    """
    Kuna ilmainfo on ingliskeelne, aga mina tahan oma kaardile kuvada eestikeelse
    teabe, siis siit tuuakse sisse inglise-eesti tõlgetega fail.
    """
    inglise_sonad = []
    eesti_sonad = []
    with open('inglise.txt', encoding = 'utf-8') as fail:
        rida = fail.readline()
        while rida != '':
            sonad = rida.split(',')
            inglise_sona = sonad[0].strip().lower()
            eesti_sona = sonad[1].strip().lower()
            inglise_sonad.append(inglise_sona)
            eesti_sonad.append(eesti_sona)
            rida = fail.readline()
    sonastik = dict(zip(inglise_sonad, eesti_sonad))
    return sonastik

def lisame_eesti_vasted():
    """
    Lisan andmefreimile ka eestikeelsed vasted ilmainfo kohta.
    """
    sonastik = inglise_eesti()
    andmed = andmetabel()
    feno_eng = andmed['fenomenid']
    eesti_vasted = []
    for fen in feno_eng:
        eestikeelne = sonastik.get(fen.lower(), None)
        eesti_vasted.append(eestikeelne)
    eesti_vasted = pd.Series(eesti_vasted)
    andmed['eesti'] = eesti_vasted.values
    return andmed

def andmed_kaardile():
    """
    Kasutan Foliumi, et andmed õige koha peale kaardile kuvada. Andmed loetakse
    andmefreimist. Tulemus salvestatakse html-faili, mis seejärel automaatselt
    brauseris avatakse.
    """
    andmed = lisame_eesti_vasted()
    m = folium.Map(location=[58.7, 25.4], zoom_start=7.5)
    for i in range(6):
        koht = andmed['kohad'][i]
        fenomen = andmed['fenomenid'][i]
        temperatuur = andmed['temperatuurid'][i]
        laiuskraad = andmed['laiuskraadid'][i]
        pikkuskraad = andmed['pikkuskraadid'][i]
        eestikeelne = andmed['eesti'][i]
        folium.Marker([laiuskraad, pikkuskraad],
                      popup=f'<strong>{koht}: {eestikeelne}. Temperatuur: {temperatuur}</strong>',
                      tooltip=f'{koht}: {eestikeelne}. Temperatuur: {temperatuur}').add_to(m)
        m.save('eesti_kaart.html')
    filename = 'eesti_kaart.html'
    webbrowser.get().open('file://' + os.path.realpath(filename))

andmed_kaardile()
