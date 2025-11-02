# Frontend - Identity Management UI

Frontend application for the Identity and Profile Management API.

## Status

Placeholder - to be implemented

## Planned Stack

- Framework: Vue.js 3 or React
- Build: Vite
- Language: TypeScript
- State: Pinia or Redux
- Deployment: Render.com

## Quick Start

(To be added when implemented)

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Architecture

The frontend will demonstrate:
- Multi-context profile management
- Guardian-minor relationships
- OAuth integration flows
- Privacy features (inspired by GDPR)

## Documentation

Detailed design documentation is available in the `docs/` directory:

- **[Name Input UX Design](./docs/name-input-ux-design.md)** - Comprehensive guide to culturally-sensitive name input flows, pattern detection, and metadata field management

### Key UX Principles

1. **Never force complexity** - Simple names stay simple
2. **Detect, don't assume** - Smart suggestions, not requirements
3. **Progressive enhancement** - Start basic, add details if needed
4. **Cultural humility** - Don't require users to know formal naming terminology
5. **Easy escape hatches** - "Use as-is" button always visible
6. **Visual examples** - Show, don't tell
7. **Locale awareness** - Use user's system locale as detection hint

