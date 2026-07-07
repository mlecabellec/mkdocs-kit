# BlockDiag — Block Flow Diagrams

BlockDiag generates flow diagrams using simple text descriptions. Nodes are connected with `->` arrows, and can carry color, shape, and label attributes.

!!! tip "Syntax"
    Nodes are auto-created when referenced. Group them with `group { }` blocks. Colors use standard CSS color names.

---

## Simple Pipeline

A basic three-stage processing pipeline showing linear data flow.

```blockdiag
{
  A [label = "Source Data"];
  B [label = "Transform"];
  C [label = "Output"];

  A -> B -> C;
}
```

---

## Build Pipeline

A branching CI/CD build pipeline with parallel test and lint stages.

```blockdiag
{
  Commit [color = lightblue];
  Build [color = lightyellow];
  Test [color = lightgreen];
  Lint [color = lightgreen];
  Package [color = orange];
  Deploy [color = lightpink];

  Commit -> Build;
  Build -> Test;
  Build -> Lint;
  Test -> Package;
  Lint -> Package;
  Package -> Deploy;
}
```

---

## MkDocs-Kit Processing Flow

The internal data flow for generating a documentation site with mkdocs-kit.

```blockdiag
{
  orientation = portrait;

  Markdown [color = lightblue];
  Plugin [label = "DiagramsPlugin", color = lightyellow];
  Renderer [label = "renderers.py"];
  HTML [color = lightgreen];
  PDF [color = orange];
  Man [label = "Man Pages", color = lightpink];

  Markdown -> Plugin;
  Plugin -> Renderer;
  Renderer -> HTML;
  HTML -> PDF;
  HTML -> Man;
}
```
