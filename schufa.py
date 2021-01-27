import sys
import requests
from bs4 import BeautifulSoup
from html2text import html2text
from requests_toolbelt import MultipartEncoder

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0"
}

baseUrl = "https://www.meineschufa.de"
postUrl = baseUrl + "/site-11_3_1"

def retrieve_token(soup):
    token = soup.find("input", {"name": "_token"})
    assert(token is not None)
    token = token["value"]

    return token

# Extract captcha link. TODO OCR this. Those are weak cpatchas
def fetch_captcha(sess,soup):
    captchaTag = soup.find("img", {"class": "captchaImage"})
    assert(captchaTag is not None)
    captchaLink = captchaTag["src"]
    img = sess.get(baseUrl + captchaLink)
    with open('captcha.png', 'wb') as f:
        f.write(img.content)


# Read user data
def get_data_send_post(sess, token):
    anrede = input("Bitte Anrede wählen [Frau/Herr]: ")
    vorname =  input("Bitte Vornamen angeben: ")
    name = input("Bitte Nachnamen angeben: ")
    geburtsdatum = input("Bitte Geburtsdatum angeben [TT.MM.JJJJ]: ")
    strasse = input("Bitte Strasse ohne Hausnummer angeben: ")
    hausnummer = input("Bitte Hausnummer angeben: ")
    plz = input("Bitte PLZ angeben: ")
    ort = input("Bitte Ort angeben: ")

    print(f"Folgende Daten werden im nächsten Schritt an die SCHUFA zur Auskunft übermittelt: {anrede} {vorname} {name} {geburtsdatum} {strasse} {hausnummer} {plz} {ort}")
    okay = input("Sollen die Daten verwendet und an die Schufa übermittelt werden? [Ja/Nein] ")

    if (not okay.lower() == "ja"):
        print("Okay... Abbruch")
        sys.exit(0)

    captcha = input(f"Bitte captcha lösen (siehe captcha.png): ")

    m_enc = MultipartEncoder(fields={
        "_token": token,
        "token": "",
        "submitted": "true",
        "anrede": anrede,
        "vorname": vorname,
        "Name": name,
        "geburtsdatum": geburtsdatum,
        "email": "",
        "geburtsname": "",
        "geburtsort": "",
        "fruehereNamen1": "",
        "fruehereNamen2": "",
        "adresse[strasse]": strasse,
        "adresse[hausnummer]": hausnummer,
        "adresse[plz]": plz,
        "adresse[ort]": ort,
        "adresse[land]": "DEU",
        "voradresse1[strasse]": "",
        "voradresse1[hausnummer]": "",
        "voradresse1[plz]": "",
        "voradresse1[ort]": "",
        "voradresse1[land]": "",
        "voradresse2[strasse]": "",
        "voradresse2[hausnummer]": "",
        "voradresse2[plz]": "",
        "voradresse2[ort]": "",
        "voradresse2[land]": "",
        "zweitadresse[strasse]": "",
        "zweitadresse[hausnummer]": "",
        "zweitadresse[plz]": "",
        "zweitadresse[ort]": "",
        "zweitadresse[land]": "",
        "document1": ("", "", "application/octet-stream"),
        "document2": ("", "", "application/octet-stream"),
        "document3": ("", "", "application/octet-stream"),
        "captcha": captcha
    })

    headers = {
        "Content-Type": m_enc.content_type,
        "User-Agent": "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0"
    }

    req = requests.Request("POST", postUrl, data=m_enc.to_string(), headers=headers)

    prepared_request = sess.prepare_request(req)

    # print the request in a curl format -- useful for debugging
    res = sess.send(prepared_request)
    soup = BeautifulSoup(res.text, "html.parser")
    with open("prefill.html", "wb") as f:
        f.write(res.text.encode('utf-8'))

    # if any error occured there will be an error field set in the response
    error = soup.find("ul", {"class": "error"})
    if error is not None and len(error.text) > 0:
        print("Es ist ein Fehler aufgetreten:")
        errorMessage = html2text(error.text)
        print(errorMessage)

        # let's try again
        fetch_captcha(sess, soup)
        form_token = retrieve_token(soup)
        return get_data_send_post(sess, form_token)

    return soup


def run_confirm(sess, soup):
    confirmPost = baseUrl + "/site-11_3_2"

    confirm_form = soup.find("form", { "action" : "/site-11_3_2" })

    m_enc = MultipartEncoder(fields={
        "_token": retrieve_token(confirm_form),
        "submitted": "true"
    })

    headers = {
        "Content-Type": m_enc.content_type,
        "User-Agent": "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0"
    }

    req = requests.Request("POST", confirmPost, data=m_enc.to_string(), headers=headers)
    prepared_request = sess.prepare_request(req)

    res = sess.send(prepared_request)
    print("Vorgang abgeschlossen. Schufa Server antwortet:")
    print(f"{res.status_code}: {html2text(res.text)}")


# Initialize a new session
sess = requests.session()

# Let's start the session
res = sess.get(baseUrl + "/index.php")
assert(res.status_code == 200)

# obtain their dakoToken url to open the form
res = sess.get(baseUrl + "/index.php?site=11_3")
assert(res.status_code == 200)
soup = BeautifulSoup(res.text, "html.parser")
link = soup.find(id="dakoLink")
assert(link is not None)
formUrl = baseUrl + link["href"]

# Get form and retrieve all necessary information
res = sess.get(formUrl, headers=headers)
soup = BeautifulSoup(res.text, "html.parser")
fetch_captcha(sess, soup)
form_token = retrieve_token(soup)
soup = get_data_send_post(sess, form_token)

content = soup.find(id="content")
assert(content is not None)

print("Text aus SCHUFA Bestätigungsdialog")
print(html2text(content.text))

confirm = input("Bestätigen und abschicken? [Ja/Nein] ")
if (confirm.lower() == "ja"):
    run_confirm(sess, soup)
else:
    print("Okay, bye!")

