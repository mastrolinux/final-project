# Identity Management Frontend

Vue 3 frontend application for the Identity and Profile Management API, providing user authentication, profile management, context switching, and administrative OAuth client management.

## Technology Stack

- Vue 3 with Composition API (`<script setup>`)
- TypeScript (strict mode)
- Pinia for state management
- Vue Router with navigation guards
- Vue I18n for internationalization
- Axios for HTTP requests
- HeadlessUI for accessible components
- Heroicons for icons

## Project Setup

```sh
npm install
```

### Development Server

```sh
npm run dev
```

The application runs at http://localhost:5173 by default.

### Production Build

```sh
npm run build
```

### Type Checking

```sh
npm run type-check
```

### Linting

```sh
npm run lint
```

## Features

### User Authentication

- Registration with email verification
- Login with JWT tokens
- Password reset flow
- Session persistence with refresh tokens

### Profile Management

- View and edit base profile
- Manage identity names (multilingual support)
- Create and manage context profiles

### Context Profiles

Six context types with inheritance from base profile:
- Professional
- Social
- Legal
- Healthcare
- Family
- Custom

### Admin Interface

Administrative features for managing OAuth clients (requires admin access):

**Access Requirements:**
- User email must be in `ADMIN_USER_EMAILS` environment variable (backend), OR
- User's `auth_users.is_admin` database column must be `true`

**Features:**
- View all registered OAuth clients
- Create new OAuth clients with configurable scopes
- Edit client configuration (name, redirect URIs, scopes)
- Soft-delete (deactivate) clients

**Location:** `/admin/oauth/clients`

The "Admin" link appears in the navigation header only for authenticated admin users.

### Theme Support

- Light, dark, and system (auto) themes
- Persisted to localStorage
- Respects system preference when set to "system"

## Project Structure

```
src/
  components/
    admin/           # Admin-only components
      OAuthClientCard.vue
      OAuthClientForm.vue
      OAuthClientSecretModal.vue
    common/          # Reusable UI components
      BaseButton.vue
      BaseCard.vue
      BaseInput.vue
      BaseModal.vue
      BaseSkeleton.vue
      ThemeToggle.vue
    layout/          # Layout components
      AppHeader.vue
    profile/         # Profile-related components
  services/          # API service layer
    admin-oauth.service.ts
    auth.service.ts
    profile.service.ts
  stores/            # Pinia stores
    auth.store.ts
    profile.store.ts
    ui.store.ts
  types/             # TypeScript interfaces
    admin-oauth.types.ts
    auth.types.ts
  views/             # Route components
    admin/
      AdminOAuthClientsView.vue
      AdminOAuthClientCreateView.vue
      AdminOAuthClientEditView.vue
  router/            # Vue Router configuration
  locales/           # i18n translation files
```

## Environment Variables

Create `.env.local` for local development:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Route Guards

The router implements several navigation guards:

- `requiresAuth`: Redirects to login if not authenticated
- `requiresGuest`: Redirects to profile if already authenticated
- `requiresVerified`: Redirects to verify-email if email not verified
- `requiresAdmin`: Redirects to home if not an admin user

## IDE Setup

Recommended: [VS Code](https://code.visualstudio.com/) with:
- [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) extension
- Disable Vetur if previously installed

## Browser DevTools

- Chrome/Edge: [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)
- Firefox: [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)

## API Integration

The frontend communicates with the backend API at the URL specified by `VITE_API_BASE_URL`. Ensure the backend is running before starting the frontend.

See `../backend/QUICK_START.md` for backend setup instructions.

## Testing OAuth Flow

To test the OAuth authorization flow:

1. Log in as an admin user
2. Navigate to Admin > OAuth Clients
3. Create a test client with appropriate redirect URIs
4. Use the client credentials to test the authorization code flow

See `../postman/TESTING-GUIDE.md` Phase 7 for detailed OAuth testing steps.
