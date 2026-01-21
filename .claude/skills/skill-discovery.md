---
name: skill-discovery
description: Discover and install relevant skills from the skills.sh catalog based on the current task. Use this when starting a new task to enhance capabilities with specialized procedural knowledge.
---

# Skill Discovery & Installation

When starting a task, check if any skills from this catalog would help. Install relevant skills to enhance your capabilities with specialized procedural knowledge.

## Installation Command

```bash
npx skills add <owner/repo>
# Or for specific skill:
npx add-skill <owner/repo> --skill <skill-name>
```

## Skills Catalog

### Frontend & UI Development
| Skill | Repository | Use When |
|-------|-----------|----------|
| vercel-react-best-practices | vercel-labs/agent-skills | Building React apps, components, hooks |
| web-design-guidelines | vercel-labs/agent-skills | UI/UX design, layouts, responsive design |
| frontend-design | anthropics/skills | Frontend implementation, CSS, styling |
| canvas-design | anthropics/skills | Canvas-based graphics, animations |
| web-artifacts-builder | anthropics/skills | Building web components, artifacts |
| theme-factory | anthropics/skills | Creating themes, design systems |

### React Native & Mobile
| Skill | Repository | Use When |
|-------|-----------|----------|
| upgrading-expo | expo/skills | Upgrading Expo SDK versions |
| building-ui | expo/skills | Building mobile UI with Expo |
| use-dom | expo/skills | DOM manipulation in React Native |
| data-fetching | expo/skills | API calls, data management in mobile |
| dev-client | expo/skills | Expo development client setup |

### Video & Media
| Skill | Repository | Use When |
|-------|-----------|----------|
| remotion-best-practices | remotion-dev/skills | Programmatic video creation |
| slack-gif-creator | anthropics/skills | Creating animated GIFs |
| algorithmic-art | anthropics/skills | Generative art, creative coding |

### Documents & Office
| Skill | Repository | Use When |
|-------|-----------|----------|
| docx | anthropics/skills | Word document generation/manipulation |
| pdf | anthropics/skills | PDF creation and processing |
| pptx | anthropics/skills | PowerPoint presentations |
| xlsx | anthropics/skills | Excel spreadsheets, data |
| doc-coauthoring | anthropics/skills | Collaborative document editing |

### Development Tools
| Skill | Repository | Use When |
|-------|-----------|----------|
| mcp-builder | anthropics/skills | Building MCP servers |
| skill-creator | anthropics/skills | Creating new skills |
| webapp-testing | anthropics/skills | Testing web applications |

### Authentication & Security
| Skill | Repository | Use When |
|-------|-----------|----------|
| better-auth-best-practices | better-auth/skills | Authentication implementation |

### Communication & Branding
| Skill | Repository | Use When |
|-------|-----------|----------|
| brand-guidelines | anthropics/skills | Brand standards, style guides |
| internal-comms | anthropics/skills | Internal communication tools |

## How to Use

1. **Before starting a task**, scan the catalog above
2. **Identify relevant skills** based on the task domain
3. **Install skills** using: `npx skills add <owner/repo>`
4. **Verify installation** with: `ls .claude/skills/`

## Example Workflow

```
Task: "Build a React dashboard with charts"

Relevant skills:
- vercel-react-best-practices (React patterns)
- web-design-guidelines (UI/UX)
- frontend-design (implementation)

Install:
$ npx skills add vercel-labs/agent-skills
$ npx skills add anthropics/skills --skill frontend-design
```

## Skill Sources

- **skills.sh** - https://skills.sh (community catalog)
- **Anthropic** - https://github.com/anthropics/skills
- **Vercel** - https://github.com/vercel-labs/agent-skills
- **Expo** - https://github.com/expo/skills
- **Remotion** - https://github.com/remotion-dev/skills

## When to Install Skills

Install skills when:
- Starting a task in a new domain
- Task requires specialized knowledge (e.g., specific framework)
- User explicitly mentions a technology in the catalog
- Current knowledge seems insufficient for the task

Do NOT install skills when:
- Task is simple and well within general capabilities
- Skills are already installed for the domain
- User is just asking questions (not implementing)
