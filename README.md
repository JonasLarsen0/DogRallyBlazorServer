README

Team 14 - Dog Rally Blazor System

Om projektet:
Vores projekt er udviklet med henblik på at give hundetrænere en brugervenlig måde at oprette og dele rally baner med hinanden. 

Installation:
1. Klon projekt: https://github.com/JonasLarsen0/DogRallyBlazorServer
2. Kør projektet
3. Opret ny bruger
4. Login med den oprettede bruger
- Alternativ: brug den eksisterende bruger: 
user: TestBruger1@test.dk
password: Testbruger1

Sikkerhed:
I vores projekt har vi brugt autorisering og autentifikation i forhold til bruger behandling. Når man starter systemet for første gang skal man registre sig som en ny bruger. Brugeren bliver gemt i en database så næste gang man starter systemet kan man logge ind med de samme oplysninger.
Vi afprøvede at benytte JWT tokens, men valgte et andet system grundet manglende viden omkring implementering af JWT tokens. Vores test udgave krævede manuel skift af token og bruger for at virke. Vi valgte i vores projekt derfor at gå med Microsoft.AspNetCore.Identity login systemet.
