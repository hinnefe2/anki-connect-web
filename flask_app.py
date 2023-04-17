import re

import requests

from bs4 import BeautifulSoup
from flask import Flask, render_template_string, request, redirect
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
auth = HTTPBasicAuth()

users = {
    "USERNAME": generate_password_hash("PASSWORD"),
}


search_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Search Page</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-aFq/bzH65dt+w6FI2ooMVUpc+21e0SRygnTpmBvdBgSdnuTN7QbdgL+OapgHtvPp" crossorigin="anonymous">

</head>
<body>
    <h1>Search Page</h1>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha2/dist/js/bootstrap.min.js" integrity="sha384-heAjqF+bCxXpCWLa6Zhcp4fu20XoNIA98ecBC1YkdXhszjoejr5y9Q77hIrv8R9i" crossorigin="anonymous"></script>
    <form autocomplete="off" action="/search-results" method="GET">
        <label for="search-query">Enter your search query:</label>
        <input type="text" id="search-query" name="query">
        <button type="submit">Search</button>
    </form>
</body>
</html>
"""


results_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Anki Flashcards from thai-language.com</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-aFq/bzH65dt+w6FI2ooMVUpc+21e0SRygnTpmBvdBgSdnuTN7QbdgL+OapgHtvPp" crossorigin="anonymous">
</head>
<body>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha2/dist/js/bootstrap.min.js" integrity="sha384-heAjqF+bCxXpCWLa6Zhcp4fu20XoNIA98ecBC1YkdXhszjoejr5y9Q77hIrv8R9i" crossorigin="anonymous"></script>
    <table id="resultsTable">
        <thead>
            <tr>
                <th>English</th>
                <th>Thai</th>
                <th>Transliterated</th>
                <th></th>
            </tr>
        </thead>
        <tbody>
            {% for item in items %}
            <tr>
                <td contenteditable autocorrect="off" autocapitalize="none">{{ item['english'] }}</td>
                <td><a href="http://www.thai-language.com/id/{{ item['id'] }}">{{ item['thai'] }}</a></td>
                <td>{{ item['transliterated'] }}</td>
                <td>
                    <form method="POST" action="/create-card">
                        <input type="hidden" name="id" value="{{ item['id'] }}">
                        <input type="hidden" name="english" id="hidden_input_{{ loop.index }}" value="{{ item['english'] }}">
                        <input type="hidden" name="thai" value="{{ item['thai'] }}">
                        <input type="hidden" name="transliterated" value="{{ item['transliterated'] }}">
                        <button type="submit" onclick="updateHiddenInputValue({{ loop.index }})">Make Card</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    <script>
        function updateHiddenInputValue(rowIndex) {
          // Get the value of the corresponding cell in the same row
          var cellValue = document.getElementById('resultsTable').rows[rowIndex].cells[0].innerHTML;
        
          // Update the value of the hidden input with the cell value
          document.getElementById('hidden_input_' + rowIndex).value = cellValue;
        }
    </script>
</body>
</html>
"""


def annotate_tones(text: str):
    return (
        text.replace("L", " \u0300 ")
        .replace("M", " \u0304 ")
        .replace("H", " \u0301 ")
        .replace("F", " \u0302 ")
        .replace("R", " \u030C ")
        .strip()
    )


def get_mp3_path(id_: int):
    resp = requests.get(f"http://www.thai-language.com/id/{id_}")

    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.content, features="lxml")

    mp3_regex = "PlayAudioFile\('(.*)'\)"

    for tag in soup.findAll("a"):
        if (onclick := tag.get("onclick")) and (
            regmatch := re.match(mp3_regex, onclick)
        ):
            return regmatch.group(1)


def query_thai_dictionary(query: str):
    resp = requests.get(
        f"http://www.thai-language.com/xml/PrefixSearch?fmt=0&input={query}"
    )

    resp.raise_for_status()

    soup = BeautifulSoup(resp.content, features="xml")

    results = [
        {
            "id": result["id"],
            "thai": result.find("t").text,
            "transliterated": annotate_tones(result.find("x").text),
            "english": result.find("e").text,
        }
        for result in soup.findAll("result")
    ]

    return results


def create_anki_note(result: dict):
    data = {
        "action": "addNote",
        "version": 6,
        "params": {
            "note": {
                "deckName": "Thai",
                "modelName": "Thai",
                "fields": {
                    "English": result["english"],
                    "Thai": result["thai"],
                    "Transliterated": result["transliterated"],
                },
                "options": {
                    "allowDuplicate": False,
                    "duplicateScope": "deck",
                    "duplicateScopeOptions": {
                        "deckName": "Default",
                        "checkChildren": False,
                        "checkAllModels": False,
                    },
                },
                "tags": ["anki-connect-web"],
            }
        },
    }

    if mp3_path := get_mp3_path(result["id"]):
        data["params"]["note"]["audio"] = [
            {
                "url": f"http://www.thai-language.com/{mp3_path}",
                "filename": f"thai_language_{mp3_path}",
                "fields": ["Audio"],
            }
        ]

    create_resp = requests.post("http://localhost:8765", json=data)

    sync_resp = requests.post(
        "http://localhost:8765", json={"action": "sync", "version": 6}
    )

    return create_resp.json(), sync_resp.json()


@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username


@app.route("/")
@auth.login_required
def index():
    return render_template_string(search_template)


@app.route("/search-results")
@auth.login_required
def search_results():
    query = request.args.get("query")

    results = query_thai_dictionary(query)

    return render_template_string(results_template, items=results)


@app.route("/create-card", methods=["POST"])
@auth.login_required
def create_card():
    result = request.form

    print(f"creating card {result}")

    create_resp, sync_resp = create_anki_note(result)

    if (create_resp["error"] or sync_resp["error"]) is not None:
        return f"Responses:<br>{create_resp}<br>{sync_resp}"

    return redirect("/", code=302)


if __name__ == "__main__":
    app.run()
