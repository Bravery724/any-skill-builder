# Goal and research

Build a skill that turns supplied project notes into a useful weekly team update. The example keeps a small scope: drafting from existing notes, not querying company systems or sending messages.

All project details, people, decisions, prompts, and sample inputs in this folder are original fictional examples. They contain no private run data. The external source below informed the question design; it is not evidence about the fictional project.

## Inspected source

- **GitLab Communication handbook**: [communication guidance](https://handbook.gitlab.com/handbook/communication/), accessed November 14, 2026. Relevant portions read: asynchronous communication, internal communication guidance, and issue cross-linking. The rest of this long handbook was not reviewed.
- **Source observation:** Written updates should carry enough context for readers, and linked information benefits from an explanation beside the link.
- **Design inference:** Ask which readers the update serves and how evidence should appear. Those choices change the context and link placement in the resulting skill.
- **Limit:** The handbook does not establish that our four questions are complete or that this generated skill outperforms another tool. Handling uncertain notes and the proposed defaults are our design choices.

## Question review

| Question | Why retain it? | Observable effect |
| --- | --- | --- |
| `readers` | Different readers need different context, even with the same facts. | Cross-functional output briefly explains project terms; team-only output can assume shared context. |
| `missing-information` | Missing information can either delay drafting or remain visible in a draft. | The selected workflow drafts with gaps; the alternative resolves material gaps before final drafting. |
| `clarification-trigger` | Necessary only when the user selects clarification first. | Defines the missing facts that should block drafting. It is inactive under the selected answer. |
| `evidence` | Traceability and reading flow can be balanced in different ways. | Selected links sit beside supported claims; the alternative groups them after the update. |

Rejected candidate: "Should the update be clear?" It does not separate meaningful behaviors. Merged candidate: a separate tone question; the user's requested natural language is already a shared requirement, not another choice to ask again.

Remaining scope gaps: this example does not decide how to handle confidential material, conflicting access permissions, automated publication, or organization-specific reporting rules. Those become relevant if the intended use extends beyond drafting from supplied public or authorized notes.
