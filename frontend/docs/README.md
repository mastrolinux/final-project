# Frontend Documentation

This directory contains design documentation for the Identity Management frontend application.

## Design Documents

### Core UX Documentation

- **[Red Routes](./red-routes.md)** - Critical user journeys with Mermaid flowcharts
  - Registration flow (landing to dashboard)
  - Login flow with error recovery
  - Profile edit flow with inheritance
  - OAuth consent flow with context selection
  - Guardian management flow
  - API endpoint mapping for each step

- **[Design System](./design-system.md)** - Visual design tokens and component patterns
  - Color palette (primary, semantic, context types)
  - Typography scale and font families
  - Spacing and border radius scales
  - Component patterns (buttons, forms, cards, modals)
  - Feedback patterns (toasts, alerts, validation)
  - Loading states and context indicators
  - Dark mode support

- **[Accessibility Guidelines](./accessibility.md)** - WCAG 2.1 AA compliance standards
  - Comprehensive compliance checklist
  - Color contrast requirements
  - Keyboard navigation patterns
  - ARIA labels and roles specification
  - Screen reader considerations
  - Focus management strategy
  - Testing checklist

- **[Responsive Design](./responsive-design.md)** - Mobile-first responsive strategy
  - Breakpoint definitions (mobile to desktop XL)
  - Layout patterns (container, grid, stack)
  - Navigation patterns per device size
  - Component adaptations (cards, forms, tables, modals)
  - Touch target sizes (minimum 44x44px)
  - Typography scaling
  - Performance considerations

### Wireframes & Visual Design

- **[Wireframes](./wireframes.md)** - Detailed screen specifications with layouts
  - 17 screen wireframes (mobile and desktop layouts)
  - Authentication screens (login, register, verification, password reset)
  - Profile management screens (view, edit, contexts)
  - OAuth consent flow with scope selection
  - Guardian dashboard and approval queue
  - Component library summary
  - Figma design file: [Identity Management API](https://www.figma.com/design/lqr70RAUSLDuI9KPKCYcGb/Identity-Management-API)

### Feature-Specific Documentation

- **[Name Input UX Design](./name-input-ux-design.md)** - Culturally-sensitive name input
  - Progressive disclosure flow (simple -> detection -> enhancement)
  - Smart pattern detection algorithm
  - Metadata field management (display_order, display_preference, etc.)
  - UI components and interactions
  - User personas and journey examples
  - Accessibility and i18n considerations

### Planned Documentation

- **API Integration** - How frontend connects to backend REST API
- **State Management** - Global state patterns using Pinia
- **Context Management** - Switching between professional, social, family contexts
- **Guardian Workflows** - UI flows for guardian-minor relationship management
- **OAuth Integration** - Third-party app authorization consent screens
- **GDPR Compliance UI** - Data export, deletion, and consent management interfaces
- **Localization Guide** - i18n implementation and translation workflows
- **Testing Strategy** - Unit, integration, and e2e testing approaches

## Design Principles

All frontend designs follow these core principles:

1. **Never force complexity** - Simple names stay simple
2. **Detect, don't assume** - Smart suggestions, not requirements
3. **Progressive enhancement** - Start basic, add details if needed
4. **Cultural humility** - Don't require users to know formal terminology
5. **Easy escape hatches** - "Use as-is" button always visible
6. **Visual examples** - Show, don't tell
7. **Locale awareness** - Use user's system locale as detection hint
8. **Privacy by design** - Make privacy the default, not an opt-in
9. **Accessibility first** - WCAG 2.1 AA compliance minimum
10. **Mobile responsive** - Touch-friendly, works on all screen sizes

## Technology Stack

### Framework
- **Vue.js 3** with Composition API (recommended)
- **TypeScript** for type safety
- **Vite** for build tooling

### UI Components
- **Headless UI** for accessible primitives
- **Custom component library** following design system
- **Tailwind CSS** for styling

### State Management
- **Pinia** for global state
- **Vue Router** for navigation
- **Vue I18n** for localization

### Testing
- **Vitest** for unit tests
- **Cypress** for e2e tests
- **Testing Library** for component tests

### Deployment
- **Render.com** static site hosting
- **GitHub Actions** for CI/CD

## File Organization

```
frontend/
├── docs/                           # Design documentation (this directory)
│   ├── README.md                  # This file
│   ├── name-input-ux-design.md   # Name input UX
│   └── [future docs]
├── src/
│   ├── components/               # Reusable components
│   │   ├── name-input/          # Name input components
│   │   ├── context-selector/    # Context switching
│   │   └── common/              # Shared UI components
│   ├── views/                   # Page-level components
│   │   ├── ProfileView.vue
│   │   ├── ContextsView.vue
│   │   └── SettingsView.vue
│   ├── stores/                  # Pinia stores
│   │   ├── user.ts
│   │   ├── profile.ts
│   │   └── contexts.ts
│   ├── services/                # API integration
│   │   ├── api.ts
│   │   └── auth.ts
│   ├── utils/                   # Helper functions
│   │   ├── nameDetection.ts    # Pattern detection logic
│   │   └── validation.ts
│   └── locales/                 # i18n translations
│       ├── en.json
│       ├── es.json
│       ├── zh.json
│       └── ar.json
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── public/                      # Static assets
```

## Contributing to Documentation

When adding new design documentation:

1. Create a new markdown file in this directory
2. Follow the existing structure and formatting
3. Include code examples where relevant
4. Add user personas/journey examples
5. Consider accessibility implications
6. Update this README with a link to the new doc

## Related Backend Documentation

Frontend design should align with backend architecture:

- [Backend Architecture Overview](../../architecture/overview.qmd)
- [Data Architecture - Cultural Naming Patterns](../../architecture/data-architecture.qmd)
- [Security Architecture - Deadname Protection](../../architecture/security-architecture.qmd)
- [Integration Architecture - Standards Compliance](../../architecture/integration-architecture.qmd)

## Questions or Feedback

For questions about frontend design decisions, refer to the specific documentation files or consult the main project documentation.

