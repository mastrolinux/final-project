# Video Pitch Script: Identity and Profile Management API
## Duration: 3-5 minutes

---

## INTRODUCTION (30 seconds)

Hi, I'm Luca. For my final year project, I'm building an Identity and Profile Management API that solves a problem almost every digital system gets wrong: **how people actually use names and present themselves in different contexts**.

Let me start with a simple question: Do you use the same name with your colleagues, your friends, your grandmother, and on LinkedIn? Probably not. Humans naturally present different facets of their identity depending on context. But nearly every digital identity system forces you into a single, rigid identity.

---

## THE PROBLEM (45 seconds)

This isn't just inconvenient - it causes real harm.

From my research, I found that:

- **90% of enterprises** experienced identity-related security incidents in 2024
- Transgender individuals are forced to use deadnames in systems that can't handle name changes properly 
-research shows that trans youth who can change their legal names have **significantly lower suicide attempt rates**

- Domestic abuse survivors can't create protective pseudonyms
- Billions of people with non-Western names cannot fit their names into systems designed around "first name, last name"

The human cost of rigid identity systems is measured in safety, dignity, and mental health.

---

## WHY CURRENT SYSTEMS FAIL (70 seconds)

So why don't existing solutions solve this? I analyzed four major approaches:

**Google Identity Platform**: Excellent for authentication, but you get one display name across all Google services. No native support for professional versus personal distinction. Multi-IdP in beta, but still maintains singular identity per provider.

**Microsoft Entra ID**: Sophisticated conditional access based on location and device, but that's for security decisions, not identity presentation. One displayName field. Custom attributes require directory extensions, and there's no concept of user-controlled personas.

**Apple Sign In with Apple**: Privacy-focused with "Hide My Email" - but that's about hiding information, not flexible identity expression. Still fundamentally single name per user.

**OpenID Connect and SCIM standards**: Great for federated authentication and automated provisioning, but they assume singular identity. The name object has givenName, familyName, middleName - there's no standard for context-specific names, no support for cultural variations beyond basic structure, and no way to express "show this name to employers, this name to friends."

**Self-Sovereign Identity and blockchain approaches**: Projects like Hyperledger Indy, Sovrin, and W3C Verifiable Credentials promise user control through decentralization. But SOUPS 2022 usability studies found the concepts are "too sophisticated for average users" - people don't want that much control, it creates burden. Users expected automatic backups but didn't realize they were solely responsible. The complexity confuses rather than empowers.

What's missing across all of them? **User-controlled, context-dependent identity presentation** that's actually usable while maintaining security. Centralized platforms solve authentication but not identity expression. Decentralized systems offer control but sacrifice usability.

My approach: A centralized API with OAuth 2.0 that gives users fine-grained control over context-specific identity without requiring them to manage cryptographic keys or blockchain wallets. The convenience of Google login with the flexibility of multiple personas.

---

## MY SOLUTION'S INNOVATION (65 seconds)

The project template asks for "a Web API to manage names and identities securely and flexibly." I'm interpreting this not as a simple CRUD API, but as a **complete identity management platform** that addresses the fundamental mismatch between how humans use identity and how systems model it.

My system is different in four key ways:

**First: Multi-context identity as core architecture.** The data model is built around contexts from day one. Professional, social, legal, healthcare contexts each with inheritance from your base profile, scope-based filtering for OAuth apps, and full user control over what's revealed where.

**Second: Cultural neutrality through flexible data structures.** No assumptions. JSONB storage following Unicode PersonNames standards. Chinese names work as well as Icelandic patronymics work as well as single-name Indonesian identities. The system adapts to your culture, not the reverse.

**Third: Guardian relationships with graduated autonomy.** Not just "admin access" - fine-grained permissions, age-appropriate transitions, immutable audit trails. When your child turns 18, the system automatically grants full autonomy. This goes beyond the template's basic requirement to address real-world family structures.

**Fourth: GDPR compliance as a design principle, not a checkbox.** All data subject rights implemented - access, rectification, erasure, portability. Every operation records its legal basis. Deadname protection built into the audit system. This is identity management that respects human dignity.

---

## TECHNOLOGY CHOICES (60 seconds)

I'm implementing this with **Python** because it's a language I know very well, which lets me focus on solving the complex domain problems rather than fighting with unfamiliar syntax.

But I'm specifically choosing **FastAPI** as the framework to explore it deeply. FastAPI offers compelling advantages:

- **Asynchronous by default** - handles thousands of concurrent requests, targeting 1000 requests per second throughput
- **Automatic OpenAPI documentation** - the API spec generates itself from type hints, critical for third-party integration
- **Native Pydantic integration** - request validation and serialization with strong type safety catches errors at the boundary
- **Performance** - benchmarks show it rivals Node.js and Go, with sub-200ms response times at the 95th percentile

For the database, I'm using **Supabase**, which I haven't worked with before, but I'm choosing it deliberately:

- **Built-in authentication** - JWT, OAuth 2.0, and multi-factor authentication out of the box
- **Row-Level Security** enforced at the PostgreSQL level - security that can't be bypassed even if application code has bugs
- Full **PostgreSQL 15+** compatibility - mature, production-grade relational features with ACID guarantees
- **JSONB support** - the perfect hybrid: structured data for security-critical fields like user IDs, flexible JSON for culturally-diverse naming that doesn't fit rigid schemas
- **Managed infrastructure** - automatic backups, point-in-time recovery, connection pooling

The architecture uses **5 layers**: presentation (REST API), application (business logic), domain (identity models), data access (repositories), and infrastructure (Supabase, Redis caching). This separation means I can swap implementations without touching business logic.

For deployment: **Render.com** for auto-scaling hosting, **Redis** for caching profile data with 5-minute TTL, and **GitHub Actions** for CI/CD with automated testing, security scanning with Bandit, and type checking with mypy before every deploy.

---

## ACADEMIC RIGOR (30 seconds)

This isn't just a technical project. I've conducted extensive background research:

- **Extensive literature review** analyzing W3C Internationalization guidelines, Unicode PersonNames specs, GDPR Articles 15-22, and academic research on context collapse and identity performance
- Real-world case studies of failed systems - Facebook's 2014 real-name policy that harmed drag queens and domestic abuse survivors, Google+'s Nymwars
- Security standards from NIST, OWASP, FIDO2

The architecture documentation includes:

- **Component architecture** with 5-layer design and sequence diagrams for OAuth flows
- **Security architecture** with 7 layers of defense-in-depth, including specific deadname protection mechanisms
- **Data model** supporting temporal versioning, multilingual JSONB storage, and guardian relationships
- **Deployment strategy** with 99.9% uptime targets, monitoring, and disaster recovery

---

## CONCLUSION (30 seconds)

Patrick McKenzie wrote in 2010: "I have never seen a computer system which handles names properly and doubt one exists, anywhere." Fifteen years later, that's still true.

I'm building a system that treats identity as what it really is - not a database field, but a complex, culturally-embedded, context-dependent aspect of human dignity.

By Week 10, I'll have a working prototype with the core API, authentication, and multi-context profiles. By the end, I'll have a production-ready system with a frontend demonstrating real use cases, full GDPR compliance, and OAuth 2.0 integration for third-party apps.

Thank you for watching. I'm excited to build this.

---

## VISUAL SUGGESTIONS FOR VIDEO

**Introduction:** Show yourself, perhaps with a simple slide showing the project title

**The Problem:** 
- Show statistics on screen: "90% of enterprises had identity-related security incidents"
- Screenshots of problematic forms asking for "First Name / Last Name"
- Brief visual of names from different cultures that don't fit

**Why Current Systems Fail:** 
- Show logos of major platforms (Google, Microsoft, Apple) 
- Show logos of SSI projects (Hyperledger Indy, Sovrin logos)
- Quote from Zuckerberg: "having two identities is an example of a lack of integrity"
- Brief visual: Centralized (too rigid) vs. Decentralized (too complex) → Your solution in the middle
- Citation: "SOUPS 2022 usability research"

**My Solution's Innovation:** 
- Show the 5-layer architecture diagram (Presentation → Application → Domain → Data Access → Infrastructure)
- Context resolution flow diagram showing how professional vs social profiles work
- Example of multilingual name storage in JSONB

**Technology Choices:** 
- Show logos: Python, FastAPI, Supabase, Redis, Render.com
- Brief code snippet showing FastAPI endpoint with automatic validation
- Diagram of defense-in-depth security layers (7 layers)

**Academic Rigor:** 
- Show your 65-page research document cover
- Security architecture diagram with OAuth flow
- Deployment topology showing Render + Supabase + Redis

**Conclusion:** Back to you with the project architecture visible in the background

---

## TIMING BREAKDOWN

- Introduction: 30 seconds
- The Problem: 45 seconds
- Why Current Systems Fail: 90 seconds (detailed evaluation of 5 approaches including SSI)
- My Solution's Innovation: 65 seconds (unique interpretation made explicit)
- Technology Choices: 70 seconds (expanded with architecture details)
- Academic Rigor: 40 seconds (more specific)
- Conclusion: 30 seconds

**Total: ~6 minutes 10 seconds**

**To reach 5 minutes exactly**, trim to:

- Why Current Systems Fail: 60 seconds (mention Google, Apple, SSI only - cut Microsoft and OIDC/SCIM)
- My Solution's Innovation: 55 seconds (trim one sentence from each point)
- Technology Choices: 60 seconds (remove Redis/GitHub Actions details)
- **New total: ~5 minutes**

**Recommendation**: The 6:10 version is more comprehensive and demonstrates deep research. Since template says "3-5 minutes," consider this an "extended pitch" option. For strict 5-minute version, use trimming suggestions above. The SSI comparison is valuable - it shows you considered decentralized alternatives and made an informed architectural choice.

## COVERAGE OF PITCH REQUIREMENTS

**Details of idea & unique interpretation**: Explicitly stated in "MY SOLUTION'S INNOVATION" - interpreting template as complete platform, not simple CRUD API

**Motivation**: "THE PROBLEM" section - 90% security incidents, trans youth suicide rates, cultural exclusion

**5 examples of similar projects evaluated**:
  1. Google Identity Platform (centralized, singular identity)
  2. Microsoft Entra ID (conditional access for security, not presentation)
  3. Apple Sign In (privacy via hiding, not flexibility)
  4. OpenID Connect/SCIM standards (no context-specific support)
  5. Self-Sovereign Identity/blockchain (Hyperledger Indy, Sovrin, W3C VCs - control but poor usability)

**Evaluation showing what's missing**: Each system evaluated with specific gaps identified:
  - Centralized platforms: solve authentication, not identity expression
  - SSI/blockchain: offers control but sacrifices usability (SOUPS 2022 research cited)
  - **Positioning**: Centralized API with OAuth 2.0 providing usable control without cryptographic complexity

