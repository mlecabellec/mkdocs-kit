# PlantUML Diagrams

PlantUML is a text-based diagramming tool that supports 13 distinct diagram types. Blocks use the `plantuml` fence identifier and must begin with `@startuml` / `@enduml` (or the equivalent for non-UML types).

---

## Sequence Diagram

Models the chronological interaction between system actors. Useful for documenting API call flows and inter-service communication.

```plantuml
@startuml
actor User
participant "REST Controller" as API
participant "OPC UA Service" as OPC
database "MongoDB" as DB

User -> API : GET /nodes
activate API
API -> OPC : browseTree(ObjectsFolder)
activate OPC
OPC --> API : OpcUaNodeDto tree
deactivate OPC
API -> DB : save(nodeSnapshot)
DB --> API : OK
API --> User : 200 JSON response
deactivate API
@enduml
```

---

## Class Diagram

Captures the static structure of a system — classes, attributes, methods, and relationships.

```plantuml
@startuml
abstract class DiagramRenderer {
  + render(src: String): String
  # validate(src: String): void
}

class PlantUmlRenderer {
  - execPath: String
  + render(src: String): String
}

class WireVizRenderer {
  + render(src: String): String
}

class BlockDiagRenderer {
  + render(src: String): String
}

DiagramRenderer <|-- PlantUmlRenderer
DiagramRenderer <|-- WireVizRenderer
DiagramRenderer <|-- BlockDiagRenderer
@enduml
```

---

## Activity Diagram

Represents the flow of control in a process — ideal for documenting build pipelines and data transformation steps.

```plantuml
@startuml
start
:Read Markdown source;
:Scan for fenced code blocks;
repeat
  :Match block type (plantuml, wireviz...);
  if (Known type?) then (yes)
    :Call renderer;
    :Replace block with SVG;
  else (no)
    :Leave block as code literal;
  endif
repeat while (More blocks?) is (yes)
:Write HTML output;
stop
@enduml
```

---

## State Diagram

Documents the lifecycle of a connection or object — perfect for documenting OPC UA connection states.

```plantuml
@startuml
[*] --> Disconnected

Disconnected --> Connecting : connect()
Connecting --> Connected : session established
Connecting --> Disconnected : timeout / error
Connected --> Subscribing : browseTree() done
Subscribing --> Active : subscriptions created
Active --> Disconnected : network drop
Active --> Active : data update received
@enduml
```

---

## Component Diagram

Shows the software component relationships and interfaces in an architecture.

```plantuml
@startuml
package "mkdocs-kit" {
  [cli.py] --> [DiagramsPlugin]
  [cli.py] --> [pdf.py]
  [cli.py] --> [man.py]
  [DiagramsPlugin] --> [renderers.py]
}

package "Third-party" {
  [plantuml] - [renderers.py]
  [WeasyPrint] - [pdf.py]
  [wireviz] - [renderers.py]
}
@enduml
```

---

## Gantt Diagram

A scheduling tool for representing project timelines with tasks and dependencies.

```plantuml
@startgantt
Project starts 2026-01-01
[Design Phase] lasts 10 days
[Core Plugin Development] lasts 15 days and starts after [Design Phase]'s end
[Diagram Renderers] lasts 10 days and starts after [Design Phase]'s end
[PDF & Man Pages] lasts 7 days and starts after [Diagram Renderers]'s end
[Tests and Validation] lasts 5 days and starts after [Core Plugin Development]'s end
[Documentation] lasts 8 days and starts after [Tests and Validation]'s end
@endgantt
```

---

## MindMap

A radial structure for capturing and organizing related concepts.

```plantuml
@startmindmap
+ MkDocs-Kit
++ Diagram Engines
+++ PlantUML
++++ Sequence
++++ Class
++++ Activity
++++ Gantt
+++ WireViz
+++ RackDiag / NwDiag
+++ PacketDiag
+++ ByteField / BlockDiag
++ Output Formats
+++ HTML (MkDocs Site)
+++ PDF (WeasyPrint)
+++ UNIX Man Pages
@endmindmap
```
