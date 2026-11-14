"""
GUI za pokretanje bezbednosnih test modula nad LOKALNOM instancom aplikacije.

Pokretanje:
    cd "security testing"
    python threat.py

Sta radi:
    - ucitava sve module iz foldera `modules/` (svaki je zaseban .py skript)
    - prikazuje ih u listi sa opisom
    - dugme "Pokreni test" izvrsava izabrani modul u zasebnoj niti
    - ispis (ctx.log / ctx.exposed / ctx.blocked) ide u konzolu dole

Svi moduli rade iskljucivo protiv adrese iz polja "Cilj" (podrazumevano
lokalna instanca aplikacije koju korisnik sam pokrene). Namena je dokumentovanje
ponasanja aplikacije pre i posle uvodjenja zastita.
"""

import importlib.util
import os
import queue
import threading
import traceback
from datetime import datetime

import tkinter as tk
from tkinter import ttk, scrolledtext

from module_base import TestContext

BASEDIR = os.path.abspath(os.path.dirname(__file__))
MODULES_DIR = os.path.join(BASEDIR, "modules")
PODRAZUMEVANI_CILJ = "http://localhost:5000"


def ucitaj_module():
    #ucita svaki .py iz modules/ kao modul; vraca listu (ime, opis, modul)
    nadjeni = []
    if not os.path.isdir(MODULES_DIR):
        return nadjeni
    for naziv in sorted(os.listdir(MODULES_DIR)):
        if not naziv.endswith(".py") or naziv.startswith("_"):
            continue
        putanja = os.path.join(MODULES_DIR, naziv)
        spec = importlib.util.spec_from_file_location(naziv[:-3], putanja)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            print(f"Modul {naziv} nije ucitan: {e}")
            continue
        if not hasattr(mod, "run"):
            continue
        ime = getattr(mod, "NAME", naziv)
        opis = getattr(mod, "DESCRIPTION", "")
        nadjeni.append((ime, opis, mod))
    return nadjeni


class App:
    def __init__(self, root):
        self.root = root
        root.title("Threat - bezbednosni test alat (lokalno)")
        root.geometry("820x600")
        root.minsize(680, 460)

        self.moduli = ucitaj_module()
        self.red = queue.Queue()        #log poruke iz radne niti -> GUI nit
        self.aktivan = False

        self._napravi_widgete()
        self._osvezi_prikaz_modula()
        self.root.after(100, self._isprazni_red)

    def _napravi_widgete(self):
        okvir = ttk.Frame(self.root, padding=10)
        okvir.pack(fill="both", expand=True)

        #--- gornji red: cilj ---
        gornji = ttk.Frame(okvir)
        gornji.pack(fill="x", pady=(0, 8))
        ttk.Label(gornji, text="Cilj (lokalna instanca):").pack(side="left")
        self.cilj_var = tk.StringVar(value=PODRAZUMEVANI_CILJ)
        ttk.Entry(gornji, textvariable=self.cilj_var, width=36).pack(side="left", padx=8)

        #--- izbor modula ---
        ttk.Label(okvir, text="Izbor testa:").pack(anchor="w")
        self.lista = tk.Listbox(okvir, height=8, exportselection=False)
        self.lista.pack(fill="x", pady=(2, 4))
        self.lista.bind("<<ListboxSelect>>", self._prikazi_opis)

        self.opis_var = tk.StringVar(value="")
        ttk.Label(okvir, textvariable=self.opis_var, foreground="#555",
                  wraplength=780, justify="left").pack(anchor="w", pady=(0, 8))

        #--- dugmad ---
        dugmad = ttk.Frame(okvir)
        dugmad.pack(fill="x", pady=(0, 8))
        self.dugme_pokreni = ttk.Button(dugmad, text="Pokreni test", command=self._pokreni)
        self.dugme_pokreni.pack(side="left")
        ttk.Button(dugmad, text="Ocisti konzolu", command=self._ocisti).pack(side="left", padx=6)
        ttk.Button(dugmad, text="Ponovo ucitaj module", command=self._reload).pack(side="left")

        #--- konzola ---
        ttk.Label(okvir, text="Konzola:").pack(anchor="w")
        self.konzola = scrolledtext.ScrolledText(okvir, height=18, wrap="word",
                                                 state="disabled", font=("Consolas", 10))
        self.konzola.pack(fill="both", expand=True)
        self.konzola.configure(background="#1e1e1e", foreground="#d4d4d4",
                               insertbackground="#d4d4d4")

    def _osvezi_prikaz_modula(self):
        self.lista.delete(0, "end")
        for ime, _opis, _mod in self.moduli:
            self.lista.insert("end", ime)
        if self.moduli:
            self.lista.selection_set(0)
            self._prikazi_opis()
        else:
            self.opis_var.set("Nema modula u folderu 'modules/'.")

    def _prikazi_opis(self, _event=None):
        idx = self._izabrani_indeks()
        if idx is None:
            return
        self.opis_var.set(self.moduli[idx][1])

    def _izabrani_indeks(self):
        sel = self.lista.curselection()
        return sel[0] if sel else None

    def _pisi(self, text=""):
        #upis u konzolu (poziva se samo iz GUI niti)
        self.konzola.configure(state="normal")
        self.konzola.insert("end", text + "\n")
        self.konzola.see("end")
        self.konzola.configure(state="disabled")

    def _ocisti(self):
        self.konzola.configure(state="normal")
        self.konzola.delete("1.0", "end")
        self.konzola.configure(state="disabled")

    def _reload(self):
        self.moduli = ucitaj_module()
        self._osvezi_prikaz_modula()
        self._pisi("[threat] Moduli ponovo ucitani.")

    def _pokreni(self):
        if self.aktivan:
            return
        idx = self._izabrani_indeks()
        if idx is None:
            self._pisi("[threat] Nije izabran test.")
            return
        ime, _opis, mod = self.moduli[idx]
        cilj = self.cilj_var.get().strip() or PODRAZUMEVANI_CILJ

        self.aktivan = True
        self.dugme_pokreni.configure(state="disabled")
        self._pisi("=" * 72)
        self._pisi(f"[{datetime.now():%H:%M:%S}] POKRENUT: {ime}")
        self._pisi("=" * 72)

        nit = threading.Thread(target=self._izvrsi, args=(mod, cilj), daemon=True)
        nit.start()

    def _izvrsi(self, mod, cilj):
        #radi u zasebnoj niti; log ide kroz thread-safe red
        def log(text=""):
            self.red.put(text)
        ctx = TestContext(target=cilj, _log=log)
        try:
            mod.run(ctx)
        except Exception:
            self.red.put("[GRESKA] Modul je prekinut izuzetkom:")
            self.red.put(traceback.format_exc())
        finally:
            self.red.put(("__KRAJ__",))

    def _isprazni_red(self):
        #periodicno prebacuje poruke iz reda u konzolu (GUI nit)
        try:
            while True:
                stavka = self.red.get_nowait()
                if isinstance(stavka, tuple) and stavka and stavka[0] == "__KRAJ__":
                    self.aktivan = False
                    self.dugme_pokreni.configure(state="normal")
                    self._pisi("")
                else:
                    self._pisi(stavka)
        except queue.Empty:
            pass
        self.root.after(100, self._isprazni_red)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
