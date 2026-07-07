# PlantUML Diagrams

This page demonstrates the 13 main diagram types supported by the PlantUML engine, as documented on [plantuml.com/fr/](https://plantuml.com/fr/).

---

## 1. Diagramme de Séquence (Sequence Diagram)
Used to show interactions between actors and objects in a chronological sequence.

```plantuml
@startuml
actor Utilisateur
boundary CLI
database BD

Utilisateur -> CLI: Lancer la compilation
activate CLI
CLI -> BD: Lire les données
activate BD
BD --> CLI: Données prêtes
deactivate BD
CLI --> Utilisateur: Compilation terminée
deactivate CLI
@enduml
```

## 2. Diagramme de Cas d'Utilisation (Usecase Diagram)
Describes the relationships between actors and the system's use cases.

```plantuml
@startuml
left to right direction
actor Client
actor Administrateur

rectangle "Système de Documentation" {
  Client -- (Consulter les pages)
  Client -- (Télécharger le PDF)
  (Générer le site) .> (Télécharger le PDF) : <<include>>
  Administrateur -- (Générer le site)
}
@enduml
```

## 3. Diagramme de Classes (Class Diagram)
Shows the static structure of the system, including classes, attributes, methods, and relationships.

```plantuml
@startuml
class Document {
  - titre: String
  - chemin: Path
  + lire(): String
}

class PageMarkdown extends Document {
  - frontmatter: Map
  + extraireContenu(): String
}

class FichierMan extends Document {
  - section: int
}
@enduml
```

## 4. Diagramme d'Activité (Activity Diagram)
Represents the flow of control or data within a system or process.

```plantuml
@startuml
start
:Lire le fichier Markdown;
if (Contient un bloc de diagramme ?) then (oui)
  :Détecter le type de diagramme;
  :Appeler le compilateur adéquat;
  :Générer le SVG;
  :Insérer le SVG dans l'HTML;
else (non)
  :Générer l'HTML brut;
endif
stop
@enduml
```

## 5. Diagramme de Composants (Component Diagram)
Illustrates how the system's software components are organized and their dependencies.

```plantuml
@startuml
[Compilateur PDF] ..> [WeasyPrint] : Utilise
[Plugin MkDocs] ..> [Compilateur PDF] : Déclenche
[Plugin MkDocs] --> [Générateurs Diagrammes] : Invoque
@enduml
```

## 6. Diagramme d'État (State Diagram)
Describes the behavior of a system or object by showing its states and transitions.

```plantuml
@startuml
[*] --> Initialisation
Initialisation --> Pret : Fichiers scannés
Pret --> EnCoursDeBuild : Commande "build"
EnCoursDeBuild --> Pret : Succès
EnCoursDeBuild --> Erreur : Échec du build
Erreur --> Pret : Fichier corrigé
@enduml
```

## 7. Diagramme d'Objets (Object Diagram)
Shows instances of classes and their concrete relationships at a specific point in time.

```plantuml
@startuml
object docIndex {
  titre = "Accueil"
  chemin = "index.md"
}

object docPlantUML {
  titre = "PlantUML"
  chemin = "uml/plantuml.md"
}

docIndex ..> docPlantUML : lie vers
@enduml
```

## 8. Diagramme de Déploiement (Deployment Diagram)
Models the physical deployment of artifacts on nodes (hardware or software execution environments).

```plantuml
@startuml
node "Poste Client" {
  node "Navigateur Web" {
    [Documentation HTML]
  }
}

node "Serveur de Fichiers" {
  [Site Statique]
}

[Navigateur Web] ..> [Site Statique] : HTTP / HTTPS
@enduml
```

## 9. Diagramme de Temps (Timing Diagram)
Used to show the state changes of one or more lifelines over a timeline.

```plantuml
@startuml
robust "Navigateur Web" as Nav
concise "Serveur Dev" as Serv

@0
Nav is Inactif
Serv is EnAttente

@100
Nav is Requete
Serv is Traitement

@200
Nav is Affichage
Serv is EnAttente
@enduml
```

## 10. Diagramme de Gantt (Gantt Diagram)
A bar chart that illustrates a project schedule.

```plantuml
@startgantt
[Phase de Conception] lasts 5 days
[Implémentation des Diagrammes] lasts 10 days
[Phase de Conception] -> [Implémentation des Diagrammes]
[Tests et Validation] lasts 3 days
[Implémentation des Diagrammes] -> [Tests et Validation]
@endgantt
```

## 11. MindMap (Carte Mentale)
A graphical way to represent ideas and concepts around a central theme.

```plantuml
@startmindmap
+ Outils MkDocs Kit
++ Diagrammes
+++ PlantUML
+++ WireViz
+++ BlockDiag
++ Documents
+++ HTML
+++ PDF
+++ UNIX Man
@endmindmap
```

## 12. WBS (Work Breakdown Structure)
A hierarchical decomposition of the total scope of work to be carried out by the project team.

```plantuml
@startwbs
* Projet Documentation
** Conception
*** Architecture
*** Choix des technologies
** Développement
*** Intégration Python
*** Wrapper PyInstaller
** Validation
*** Jeux de tests
@endwbs
```

## 13. Diagramme Réseau (Network Diagram / NwDiag)
Visualizes network topologies, subnets, and IP addresses.

```plantuml
@startuml
nwdiag {
  network dmz {
    web01 [address = "192.168.1.10"];
    web02 [address = "192.168.1.11"];
  }
  network internal {
    web01;
    web02;
    db01 [address = "10.0.0.100", shape = database];
  }
}
@enduml
```

