# report_project_FastAPI

**report_project_FastAPI** je web aplikacija temeljena na MVC (Model-View-Controller) arhitekturi, izrađena u FastAPI. Aplikacija omogućava unos ulaznih računa i izvještavanje o ukupnim troškovima po mjestima troška.

## Sadržaj

- [Pokretanje servera](#pokretanje-servera)
- [Struktura aplikacije](#struktura-aplikacije)
- [Funkcionalnosti](#funkcionalnosti)
- [Tehnologije](#tehnologije)

---

## Pokretanje servera

Kako biste pokrenuli projekt lokalno, pratite sljedeće korake:

1. **Klonirajte repozitorij**:

    Ako preuzimate projekt s GitHub-a, klonirajte repozitorij koristeći `git clone`:

    ```bash
    git clone https://github.com/anasicic/report_project_FastAPI.git
    ```


2. **Idite u direktorij projekta**:

    Nakon što je projekt kloniran, uđite u direktorij projekta:

    ```bash
    cd app
    ```

3. **Stvorite virtualno okruženje**:

    Preporučuje se koristiti virtualno okruženje za instalaciju paketa:

    ```bash
    python -m venv venv
    ```

4. **Aktivirajte virtualno okruženje**:

    Na Windows sustavima:

    ```bash
    venv\Scripts\activate
    ```

    Na Linux ili macOS sustavima:

    ```bash
    source venv/bin/activate
    ```

5. **Instalirajte potrebne pakete**:

    ```bash
    pip install -r requirements.txt
    ```

6. **Pokrenite razvojni server**:

    ```bash
    uvicorn main:app --reload
    ```

7. **Otvorite preglednik i idite na**:

    ```url
    http://127.0.0.1:8000/
    ```

---

## Struktura aplikacije


Aplikacija se sastoji od nekoliko modula unutar direktorija `app`, uključujući:

- **auth.py**: Ovaj modul upravlja autentifikacijom korisnika. Uključuje funkcionalnosti za prijavu, registraciju i odjavu korisnika. Pruža i zaštitu ruta kako bi se osiguralo da samo prijavljeni korisnici imaju pristup određenim dijelovima aplikacije.

- **admin.py**: Modul za administrativne funkcije. Ovdje se nalaze endpointi koji omogućuju administratorima dodavanje, brisanje ili uređivanje korisnika, dobavljača, vrsta troškova, mjesta troškova te kreiranje izvještaja o ukupnim troškovima po mjestima troška.

- **invoices.py**: Ovaj modul upravlja svim funkcijama vezanim uz ulazne račune. Uključuje mogućnosti za unos, ažuriranje, brisanje i pregled računa.

- **users.py**: Modul koji upravlja korisničkim podacima. Ovdje se nalaze funkcionalnosti za dobivanje informacija o korisnicima, njihovo ažuriranje i upravljanje korisničkim profilima.


---

## Funkcionalnosti

- **Korisnička autentifikacija**: Prijava, registracija, odjava.
- **Administratorske funkcije**: Dodavanje i brisanje korisnika, dobavljača, vrste troškova, mjesta troškova, generiranje izvještaja.
- **Upravljanje ulaznim računima**: Unos, ažuriranje i brisanje računa.
- **Vizualizacija podataka**: Izvještaj o troškovima s grafičkim prikazima i opcijom izvoza u Excel.

---

## Tehnologije

- **FastAPI** - Web framework za backend
- **SQLite** - Baza podataka

