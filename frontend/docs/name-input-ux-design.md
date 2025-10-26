# Name Input UX Design

## Overview

This document describes the user experience design for culturally-sensitive name input in the Identity Management system. The design supports diverse global naming patterns without requiring users to understand naming taxonomy or forcing unnecessary complexity.

## Core Design Principles

1. **Never force complexity** - Simple names stay simple
2. **Detect, don't assume** - Smart suggestions, not requirements
3. **Progressive enhancement** - Start basic, add details if needed
4. **Cultural humility** - Don't require users to know formal terminology
5. **Easy escape hatches** - "Use as-is" button always visible
6. **Visual examples** - Show, don't tell
7. **Locale awareness** - Use user's system locale as detection hint

---

## Progressive Name Input Flow

### Stage 1: Universal Simple Start

**Goal**: Let users enter their name naturally without forcing them to choose a "pattern"

**UI Components**:
```jsx
<NameInputWizard>
  <Step1_SimpleInput>
    <h2>What should we call you?</h2>
    <p>Enter your name as you'd like it to appear</p>
    
    <Input
      name="full_name_input"
      label="Full Name"
      placeholder="Enter your full name"
      autoComplete="name"
      onChange={handleNameInput}
      value={userInput}
    />
    
    <Examples>
      <small>
        Examples: "Maria Garcia Rodriguez" · "习近平" · "Sukarno" · "Dr. Sarah Chen"
      </small>
    </Examples>

    <Button onClick={handleSimpleContinue}>Continue</Button>
  </Step1_SimpleInput>
</NameInputWizard>
```

**Design notes**:
- Single input field reduces cognitive load
- Examples adapt based on user's browser locale
- No jargon or technical terminology
- AutoComplete attribute helps browser pre-fill

---

### Stage 2: Smart Pattern Detection

**Goal**: Analyze user input and suggest appropriate name structure without interrupting flow

#### Detection Algorithm

```javascript
function detectNamePattern(input) {
  const detections = [];
  
  // Detection signals
  const hasCJK = /[\u4E00-\u9FFF\u3400-\u4DBF]/.test(input);
  const hasArabicScript = /[\u0600-\u06FF]/.test(input);
  const hasTamilScript = /[\u0B80-\u0BFF]/.test(input);
  const hasMultipleSpaces = (input.match(/ /g) || []).length >= 3;
  const hasInitialDot = /^[A-Z]\. /.test(input);
  const words = input.split(/\s+/);
  
  // Detection logic with confidence scores
  
  if (hasCJK && words.length === 1) {
    detections.push({
      pattern: "chinese",
      confidence: "high",
      reason: "Single word with CJK characters",
      suggestion: "This looks like an East Asian name. Would you like to add romanization?",
      fields: ["family.zh", "given.zh", "family.en", "given.en"],
      metadata: ["display_order"]
    });
  }
  
  if (hasArabicScript) {
    detections.push({
      pattern: "arabic",
      confidence: "high",
      reason: "Arabic script detected",
      suggestion: "We can help you add multiple name components (ism, nasab, nisba)",
      fields: ["ism", "kunya", "nasab", "nisba"],
      metadata: ["display_preference"]
    });
  }
  
  if (words.length >= 3 && !hasCJK && !hasArabicScript) {
    detections.push({
      pattern: "spanish",
      confidence: "medium",
      reason: "Multiple surnames detected",
      suggestion: `Do "${words.slice(-2)[0]}" and "${words.slice(-1)[0]}" represent your paternal and maternal surnames?`,
      fields: ["given", "paternal_surname", "maternal_surname"],
      metadata: ["legal_surname_order", "international_display"]
    });
  }
  
  if (hasInitialDot) {
    detections.push({
      pattern: "tamil",
      confidence: "high",
      reason: "Patronymic initial pattern detected",
      suggestion: "Would you like to expand this to show your father's full name in some contexts?",
      fields: ["patronymic_initial", "given", "father_name"],
      metadata: []
    });
  }
  
  if (words.length === 1 && !hasCJK && !hasArabicScript) {
    detections.push({
      pattern: "mononym",
      confidence: "medium",
      reason: "Single name entered",
      suggestion: "We notice you have a single name. That's completely valid!",
      fields: ["full_name"],
      metadata: []
    });
  }
  
  // Default: Western pattern
  if (detections.length === 0) {
    detections.push({
      pattern: "western",
      confidence: "low",
      reason: "Standard format",
      suggestion: "We'll treat this as a given name and family name",
      fields: ["given", "family"],
      metadata: []
    });
  }
  
  return detections[0]; // Return highest confidence
}
```

#### User Confirmation UI

```jsx
<Step2_PatternDetection>
  <h2>We detected: {getPatternDisplayName(detection.pattern)}</h2>
  
  <DetectionCard>
    <Icon>{getPatternIcon(detection.pattern)}</Icon>
    <Message>{detection.suggestion}</Message>
    <ConfidenceBadge level={detection.confidence}>
      {detection.confidence} confidence
    </ConfidenceBadge>
  </DetectionCard>

  <ConfirmationOptions>
    <Option onClick={() => confirmPattern(detection.pattern)}>
      <CheckIcon />
      <div>
        <strong>Yes, that's correct</strong>
        <Preview>Your name will be stored as: {getPreview(detection.pattern)}</Preview>
      </div>
    </Option>

    <Option onClick={showAllPatterns}>
      <EditIcon />
      <div>
        <strong>No, let me choose a different format</strong>
        <small>See all naming patterns</small>
      </div>
    </Option>

    <Option onClick={useSimpleFormat}>
      <SimpleIcon />
      <div>
        <strong>Keep it simple - use as entered</strong>
        <small>We'll store "{userInput}" as-is without special formatting</small>
      </div>
    </Option>
  </ConfirmationOptions>
</Step2_PatternDetection>
```

**Design notes**:
- Show detection with clear explanation
- Three options: confirm, choose different, or keep simple
- Live preview of how name will be stored
- Confidence indicator helps user understand system's certainty

---

### Stage 3a: Enhanced Input (Pattern Confirmed)

#### Example: Chinese Name Enhancement

```jsx
<Step3_EnhancedInput pattern="chinese">
  <h2>Enhance your name with multiple languages</h2>
  <p>You entered: <strong>{originalInput}</strong></p>
  
  <AutoParsed>
    <Alert type="info">
      We automatically separated this into:
      <div>Family name: {parsedFamily}</div>
      <div>Given name: {parsedGiven}</div>
    </Alert>
  </AutoParsed>

  <FieldGroup label="Family Name" collapsible defaultOpen>
    <Input 
      name="family.zh" 
      label="Chinese Characters" 
      value={parsedFamily}
      lang="zh"
    />
    <Input 
      name="family.zh-Latn" 
      label="Pinyin (Optional)" 
      placeholder="e.g., Xi"
      helpText="Helps with pronunciation"
    />
    <Input 
      name="family.en" 
      label="English/Romanized (Optional)" 
      placeholder="e.g., Xi"
    />
  </FieldGroup>

  <FieldGroup label="Given Name" collapsible defaultOpen>
    <Input name="given.zh" label="Chinese Characters" value={parsedGiven} />
    <Input name="given.zh-Latn" label="Pinyin (Optional)" placeholder="e.g., Jinping" />
    <Input name="given.en" label="English/Romanized (Optional)" placeholder="e.g., Jinping" />
  </FieldGroup>

  {/* Metadata Field: Display Order */}
  <MetadataSection>
    <SimpleQuestion>
      <Label>How should your name be ordered in English?</Label>
      <RadioGroup name="display_order" defaultValue="family_first">
        <Radio value="family_first">
          <strong>{parsedFamily} {parsedGiven}</strong> (family name first)
          <Badge variant="success">Recommended</Badge>
          <Hint>Traditional Chinese order - Xi Jinping</Hint>
        </Radio>
        <Radio value="given_first">
          <strong>{parsedGiven} {parsedFamily}</strong> (given name first)
          <Hint>Western style - Jinping Xi</Hint>
        </Radio>
        <Radio value="context_aware">
          <strong>Automatic</strong> (adapt to audience language)
          <Hint>Show "习近平" in Chinese, "Xi Jinping" in English</Hint>
        </Radio>
      </RadioGroup>
    </SimpleQuestion>

    <LivePreview>
      <Label>Preview: How your name appears</Label>
      <PreviewCard>
        <PreviewItem>
          <Flag>🇨🇳</Flag>
          <Locale>Chinese (zh-CN):</Locale>
          <NameDisplay>{getChineseDisplay()}</NameDisplay>
        </PreviewItem>
        <PreviewItem>
          <Flag>🇺🇸</Flag>
          <Locale>English (en-US):</Locale>
          <NameDisplay>{getEnglishDisplay()}</NameDisplay>
        </PreviewItem>
      </PreviewCard>
    </LivePreview>
  </MetadataSection>

  <Actions>
    <Button variant="primary" onClick={handleSave}>Save Name</Button>
    <Button variant="secondary" onClick={goBack}>Go Back</Button>
  </Actions>
</Step3_EnhancedInput>
```

#### Example: Arabic Name Enhancement

```jsx
<Step3_EnhancedInput pattern="arabic">
  <h2>Arabic Name Components</h2>
  <Hint>All fields optional - enter only what applies to you</Hint>
  
  <FieldGroup label="Ism (Given Name - اسم)" optional>
    <Input name="ism.ar" label="Arabic" placeholder="محمد" dir="rtl" lang="ar" />
    <Input name="ism.ar-Latn" label="Romanized" placeholder="Muhammad" />
    <Input name="ism.en" label="English" placeholder="Muhammad" />
    <HelpText>Your personal given name</HelpText>
  </FieldGroup>
  
  <FieldGroup label="Kunya (Honorific - كنية)" optional>
    <Input name="kunya.ar" label="Arabic" placeholder="أبو عبد الله" dir="rtl" />
    <Input name="kunya.ar-Latn" label="Romanized" placeholder="Abu Abdullah" />
    <HelpText>
      Honorific name, often "Abu [child's name]" (father of)
    </HelpText>
  </FieldGroup>
  
  <FieldGroup label="Nasab (Lineage - نسب)" optional>
    <Input name="nasab.ar" label="Arabic" placeholder="بن عبد الله" dir="rtl" />
    <Input name="nasab.ar-Latn" label="Romanized" placeholder="ibn Abdullah" />
    <HelpText>
      Patronymic - "ibn/bin [father's name]" (son of)
    </HelpText>
  </FieldGroup>
  
  <FieldGroup label="Nisba (Family/Tribal - نسبة)" optional>
    <Input name="nisba.ar" label="Arabic" placeholder="الهاشمي" dir="rtl" />
    <Input name="nisba.ar-Latn" label="Romanized" placeholder="al-Hashimi" />
    <HelpText>Family, tribal, or place name affiliation</HelpText>
  </FieldGroup>

  {/* Metadata Field: Display Preference */}
  <MetadataSection>
    <SimpleQuestion>
      <Label>How should your name typically appear?</Label>
      <RadioGroup name="display_preference" defaultValue="formal_short">
        <Radio value="formal_full">
          <NameExample>Muhammad ibn Abdullah al-Hashimi</NameExample>
          <Description>Full formal - all components</Description>
          <UseCase>Official documents, very formal contexts</UseCase>
        </Radio>
        <Radio value="formal_short">
          <NameExample>Muhammad al-Hashimi</NameExample>
          <Description>Standard formal - ism + nisba</Description>
          <UseCase>Professional settings, default</UseCase>
          <Badge>Recommended</Badge>
        </Radio>
        <Radio value="informal">
          <NameExample>Muhammad</NameExample>
          <Description>Informal - given name only</Description>
          <UseCase>Casual contexts, friends</UseCase>
        </Radio>
        <Radio value="kunya">
          <NameExample>Abu Abdullah</NameExample>
          <Description>Honorific - kunya</Description>
          <UseCase>Respectful informal address</UseCase>
        </Radio>
      </RadioGroup>
    </SimpleQuestion>

    <AdvancedOptions collapsible>
      <Checkbox name="allow_context_override">
        Allow different formats in different contexts
        <Hint>
          E.g., Professional context uses "formal_full", 
          Social context uses "informal"
        </Hint>
      </Checkbox>
    </AdvancedOptions>

    <LivePreview>
      <Label>Preview across contexts</Label>
      <PreviewCard>
        <PreviewItem>
          <Context>Formal:</Context>
          <NameDisplay>{getFormalDisplay()}</NameDisplay>
        </PreviewItem>
        <PreviewItem>
          <Context>Standard:</Context>
          <NameDisplay>{getStandardDisplay()}</NameDisplay>
        </PreviewItem>
        <PreviewItem>
          <Context>Casual:</Context>
          <NameDisplay>{getCasualDisplay()}</NameDisplay>
        </PreviewItem>
      </PreviewCard>
    </LivePreview>
  </MetadataSection>
</Step3_EnhancedInput>
```

#### Example: Spanish Double Surname

```jsx
<Step3_EnhancedInput pattern="spanish">
  <h2>Spanish/Portuguese Name</h2>
  
  <FieldGroup label="Given Name (Nombre)">
    <Input name="given.es" label="Spanish" placeholder="María" />
    <Input name="given.en" label="English" placeholder="Maria" />
  </FieldGroup>
  
  <FieldGroup label="Paternal Surname (Apellido Paterno)">
    <Input name="paternal_surname.es" placeholder="García" />
    <HelpText>Your father's first surname</HelpText>
  </FieldGroup>
  
  <FieldGroup label="Maternal Surname (Apellido Materno)">
    <Input name="maternal_surname.es" placeholder="Rodríguez" />
    <HelpText>Your mother's first surname (her paternal surname)</HelpText>
  </FieldGroup>

  {/* Metadata Field: Surname Order */}
  <MetadataSection>
    <SimpleQuestion>
      <Label>Legal surname order</Label>
      <DragAndDrop 
        items={['paternal', 'maternal']}
        onChange={handleSurnameOrderChange}
        name="legal_surname_order"
      >
        <DraggableItem value="paternal">
          <DragHandle />
          Paternal ({paternalSurname})
          <Badge>Standard</Badge>
        </DraggableItem>
        <DraggableItem value="maternal">
          <DragHandle />
          Maternal ({maternalSurname})
        </DraggableItem>
      </DragAndDrop>
      
      <Hint>
        Most common: Paternal → Maternal (García Rodríguez)
        <br />
        Some regions allow: Maternal → Paternal
      </Hint>
    </SimpleQuestion>

    {/* Metadata Field: International Display */}
    <SimpleQuestion>
      <Label>International/informal display preference</Label>
      <RadioGroup name="international_display" defaultValue="both">
        <Radio value="both">
          <NameExample>María García Rodríguez</NameExample>
          <Description>Both surnames</Description>
          <UseCase>Full formal name</UseCase>
        </Radio>
        <Radio value="paternal_only">
          <NameExample>María García</NameExample>
          <Description>Paternal surname only</Description>
          <UseCase>Common in casual contexts</UseCase>
        </Radio>
        <Radio value="hyphenated">
          <NameExample>María García-Rodríguez</NameExample>
          <Description>Hyphenated</Description>
          <UseCase>International forms requiring single surname</UseCase>
        </Radio>
      </RadioGroup>
    </SimpleQuestion>

    <LivePreview>
      <Label>Preview</Label>
      <PreviewCard>
        <PreviewItem>
          <Context>Legal documents:</Context>
          <NameDisplay>{getLegalNameDisplay()}</NameDisplay>
        </PreviewItem>
        <PreviewItem>
          <Context>Informal:</Context>
          <NameDisplay>{getInformalDisplay()}</NameDisplay>
        </PreviewItem>
        <PreviewItem>
          <Context>International:</Context>
          <NameDisplay>{getInternationalDisplay()}</NameDisplay>
        </PreviewItem>
      </PreviewCard>
    </LivePreview>
  </MetadataSection>
</Step3_EnhancedInput>
```

---

### Stage 3b: Manual Pattern Selection

**When user clicks "Show all patterns"**

```jsx
<Step3_PatternSelector>
  <h2>Choose your naming pattern</h2>
  <p>Select the format that best matches your cultural background</p>

  <PatternGrid>
    <PatternCard onClick={() => selectPattern("western")}>
      <Icon>👤</Icon>
      <Title>Western/Standard</Title>
      <Example>Sarah Johnson, John Smith</Example>
      <Description>Given name + Family name</Description>
      <Languages>English, French, German, etc.</Languages>
      <Badge variant="primary">Most common</Badge>
    </PatternCard>

    <PatternCard onClick={() => selectPattern("chinese")}>
      <Icon>🇨🇳</Icon>
      <Title>East Asian</Title>
      <Example>习近平 (Xi Jinping), 田中太郎</Example>
      <Description>Family-first ordering with romanization support</Description>
      <Languages>Chinese · Japanese · Korean · Vietnamese</Languages>
    </PatternCard>

    <PatternCard onClick={() => selectPattern("arabic")}>
      <Icon>🇸🇦</Icon>
      <Title>Arabic</Title>
      <Example>محمد بن عبد الله (Muhammad ibn Abdullah)</Example>
      <Description>Multi-component names (ism, nasab, nisba)</Description>
      <Languages>Arabic · Persian</Languages>
    </PatternCard>

    <PatternCard onClick={() => selectPattern("spanish")}>
      <Icon>🇪🇸</Icon>
      <Title>Spanish/Portuguese</Title>
      <Example>María García Rodríguez</Example>
      <Description>Given + Paternal surname + Maternal surname</Description>
      <Languages>Spanish · Portuguese · Latin American</Languages>
    </PatternCard>

    <PatternCard onClick={() => selectPattern("tamil")}>
      <Icon>🇮🇳</Icon>
      <Title>South Indian</Title>
      <Example>S. Rajeev, K. Vijay</Example>
      <Description>Patronymic initial + Given name</Description>
      <Languages>Tamil · Telugu · Kannada</Languages>
    </PatternCard>

    <PatternCard onClick={() => selectPattern("mononym")}>
      <Icon>⭐</Icon>
      <Title>Single Name (Mononym)</Title>
      <Example>Sukarno, Madonna</Example>
      <Description>Just one name, no family name</Description>
      <Languages>Indonesian · Icelandic · Stage names</Languages>
    </PatternCard>

    <PatternCard onClick={() => selectPattern("custom")}>
      <Icon>✏️</Icon>
      <Title>Custom/Other</Title>
      <Example>Your unique naming tradition</Example>
      <Description>Build your own name structure</Description>
      <Badge variant="info">Advanced</Badge>
    </PatternCard>
  </PatternGrid>

  <SearchBar>
    <SearchIcon />
    <Input 
      placeholder="Search by country or culture (e.g., 'Iceland', 'Nigeria', 'Thailand')"
      onChange={handlePatternSearch}
    />
  </SearchBar>

  <HelpSection>
    <HelpLink onClick={() => showNamingGuide()}>
      📖 Not sure which pattern fits? See our naming guide
    </HelpLink>
    <HelpLink onClick={() => showExamples()}>
      🌍 Browse examples from around the world
    </HelpLink>
  </HelpSection>
</Step3_PatternSelector>
```

**Design notes**:
- Visual cards with clear examples
- Language hints help users identify their pattern
- Search functionality for quick access
- Help links for uncertain users

---

## Alternative: Real-Time Smart Suggestions

**For more advanced UX, show contextual suggestions as user types:**

```jsx
<SmartNameInput>
  <Input
    name="full_name"
    label="Full Name"
    value={input}
    onChange={handleSmartInput}
    onFocus={handleFocus}
  />

  {/* Smart suggestions appear below input */}
  {input && suggestions.length > 0 && (
    <SmartSuggestions>
      {suggestions.map(suggestion => (
        <Suggestion key={suggestion.type} onClick={() => applySuggestion(suggestion)}>
          <SuggestionIcon>{suggestion.icon}</SuggestionIcon>
          <SuggestionContent>
            <SuggestionTitle>{suggestion.title}</SuggestionTitle>
            <SuggestionDescription>{suggestion.description}</SuggestionDescription>
          </SuggestionContent>
          <ApplyButton>Apply</ApplyButton>
        </Suggestion>
      ))}
    </SmartSuggestions>
  )}
</SmartNameInput>
```

**Example suggestions:**

```javascript
// User types: "S. Rajeev"
{
  icon: "💡",
  title: "Expand patronymic initial?",
  description: "Looks like you have a name initial (S.). Want to add your father's full name?",
  action: "expandPatronymic"
}

// User types: "习近平"
{
  icon: "🌏",
  title: "Add romanization?",
  description: "Help people pronounce your name in English/international contexts",
  action: "addRomanization"
}

// User types: "María García Rodríguez"
{
  icon: "📋",
  title: "Specify surname structure?",
  description: "Clarify which are paternal and maternal surnames for official documents",
  action: "clarifySpanishSurnames"
}
```

---

## Metadata Fields UI Summary

### How Metadata Fields are Presented

| Metadata Field | Pattern | UI Component | User-Friendly Label | Default Value |
|----------------|---------|--------------|---------------------|---------------|
| `display_order` | Chinese, East Asian | Radio buttons | "How should your name be ordered in English?" | `family_first` |
| `display_preference` | Arabic, Complex | Radio buttons with examples | "How should your name typically appear?" | `formal_short` |
| `legal_surname_order` | Spanish, Portuguese | Drag-and-drop list | "Legal surname order" | `["paternal", "maternal"]` |
| `international_display` | Spanish, Portuguese | Radio buttons | "International/informal display preference" | `both` |
| `allow_context_override` | All patterns | Checkbox (advanced) | "Allow different formats in different contexts" | `false` |

### Design Patterns for Metadata

1. **Use natural language questions** - Not "Set display_order parameter" but "How should your name be ordered?"
2. **Show examples with each option** - Visual previews reduce confusion
3. **Provide reasonable defaults** - Based on cultural norms
4. **Live preview updates** - Show impact of changes immediately
5. **Progressive disclosure** - Advanced options collapsed by default

---

## User Personas and Examples

### Persona 1: Maria (Spanish user)

**Input**: "María García Rodríguez"

**Detection**:
- Pattern: Spanish
- Confidence: Medium (3 words, locale es-ES)
- Suggestion: "We detected two surnames. Is García your paternal and Rodríguez your maternal surname?"

**User Journey**:
1. Confirms detection
2. System auto-fills fields
3. User reviews surname order (drag-and-drop shows Paternal → Maternal)
4. User selects "Both surnames" for international display
5. Saves

**Result**:
```json
{
  "names": {
    "given": {"es": "María", "en": "Maria"},
    "paternal_surname": {"es": "García"},
    "maternal_surname": {"es": "Rodríguez"},
    "legal_surname_order": ["paternal", "maternal"],
    "international_display": "both"
  }
}
```

---

### Persona 2: Wei (Chinese user in US)

**Input**: "李明"

**Detection**:
- Pattern: Chinese
- Confidence: High (CJK characters, single word)
- Suggestion: "Add English spelling? This helps colleagues pronounce your name"

**User Journey**:
1. Confirms detection
2. System parses: Family=李, Given=明
3. User adds romanization: Li, Ming
4. Question: "Should this be 'Li Ming' or 'Ming Li' in English?"
5. User selects "Automatic (adapt to context)"
6. Saves

**Result**:
```json
{
  "names": {
    "family": {"zh": "李", "en": "Li"},
    "given": {"zh": "明", "en": "Ming"},
    "display_order": "context_aware",
    "full_name": {"zh": "李明", "en": "Li Ming"}
  }
}
```

---

### Persona 3: Sarah (Western user)

**Input**: "Sarah Johnson"

**Detection**:
- Pattern: Western
- Confidence: Low (default)
- Suggestion: "We'll treat this as a given name and family name"

**User Journey**:
1. Confirms detection (or clicks "Keep it simple")
2. System auto-parses: Given=Sarah, Family=Johnson
3. No complex metadata needed
4. Saves

**Result**:
```json
{
  "names": {
    "given": {"en": "Sarah"},
    "family": {"en": "Johnson"}
  }
}
```

---

### Persona 4: Sukarno (Mononym)

**Input**: "Sukarno"

**Detection**:
- Pattern: Mononym
- Confidence: Medium (single word, no CJK)
- Suggestion: "We notice you have a single name - that's perfectly valid!"

**User Journey**:
1. Confirms mononym pattern
2. System stores as full_name (no forced splitting)
3. Saves

**Result**:
```json
{
  "names": {
    "full_name": {"id": "Sukarno", "en": "Sukarno"}
  }
}
```

---

### Persona 5: Muhammad (Arabic user)

**Input**: "محمد بن عبد الله الهاشمي"

**Detection**:
- Pattern: Arabic
- Confidence: High (Arabic script)
- Suggestion: "We can help you add multiple name components"

**User Journey**:
1. Confirms detection
2. System suggests parsing: ism=محمد, nasab=بن عبد الله, nisba=الهاشمي
3. User adds romanization to each component
4. User selects display_preference: "formal_short" (Muhammad al-Hashimi)
5. Saves

**Result**:
```json
{
  "names": {
    "ism": {"ar": "محمد", "ar-Latn": "Muhammad", "en": "Muhammad"},
    "nasab": {"ar": "بن عبد الله", "ar-Latn": "ibn Abdullah"},
    "nisba": {"ar": "الهاشمي", "ar-Latn": "al-Hashimi"},
    "display_preference": "formal_short"
  }
}
```

---

## Context-Specific Overrides

Users can override default display preferences for specific contexts:

```jsx
<ContextOverrideModal context="professional">
  <h3>Professional Context - Name Display</h3>
  
  <CurrentDefault>
    <Label>Current default setting:</Label>
    <Display>{getDefaultDisplay()}</Display>
    <Example>"Muhammad al-Hashimi" (formal_short)</Example>
  </CurrentDefault>

  <InheritanceToggle>
    <Checkbox 
      name="use_default_display" 
      checked={useDefault}
      onChange={handleDefaultToggle}
    >
      Use default display settings
    </Checkbox>
  </InheritanceToggle>

  {!useDefault && (
    <OverrideOptions>
      <Label>Override for professional context:</Label>
      <RadioGroup name="context_display_preference">
        <Radio value="formal_full">
          <NameExample>Muhammad ibn Abdullah al-Hashimi</NameExample>
          <Description>Full formal name with all components</Description>
        </Radio>
        <Radio value="formal_short">
          <NameExample>Muhammad al-Hashimi</NameExample>
          <Description>Standard formal (inherited default)</Description>
        </Radio>
        <Radio value="custom">
          <NameExample>
            <Input placeholder="Dr. Muhammad al-Hashimi" />
          </NameExample>
          <Description>Custom display for this context</Description>
        </Radio>
      </RadioGroup>
    </OverrideOptions>
  )}

  <Actions>
    <Button variant="primary" onClick={handleSaveOverride}>
      Save Context Override
    </Button>
    <Button variant="secondary" onClick={handleCancel}>
      Cancel
    </Button>
  </Actions>
</ContextOverrideModal>
```

---

## Implementation Recommendations

### Frontend Framework

**Recommended**: Vue.js 3 with Composition API

**Reasons**:
- Reactive data binding perfect for live previews
- v-model directives simplify form handling
- Teleport for modals/overlays
- Excellent i18n support (vue-i18n)
- TypeScript support

**Alternative**: React with hooks

---

### Component Library

**Recommended**: Custom components with Headless UI

**Core components needed**:
- `NameInput` - Main input field with autocomplete
- `PatternDetector` - Background detection service
- `PatternSelector` - Visual pattern selection grid
- `EnhancedFieldSet` - Pattern-specific field groups
- `LivePreview` - Real-time name display preview
- `DragAndDropList` - For surname ordering
- `ContextOverrideModal` - Context-specific settings

---

### State Management

**Recommended**: Pinia (Vue) or Zustand (React)

**State structure**:
```typescript
interface NameInputState {
  currentStep: 'simple' | 'detection' | 'enhanced' | 'pattern-select';
  userInput: string;
  detectedPattern: DetectionResult | null;
  selectedPattern: NamePattern | null;
  nameData: NameStructure;
  metadata: {
    display_order?: string;
    display_preference?: string;
    legal_surname_order?: string[];
    international_display?: string;
  };
  validation: ValidationState;
}
```

---

### Accessibility Considerations

1. **Screen reader support**:
   - Announce pattern detection results
   - Describe what each metadata option means
   - Provide text alternatives for visual previews

2. **Keyboard navigation**:
   - All interactions must work without mouse
   - Drag-and-drop should have keyboard alternative
   - Radio buttons navigable with arrow keys

3. **RTL language support**:
   - Arabic input fields must have `dir="rtl"`
   - Layout should flip for RTL languages
   - Mixed LTR/RTL text handling

4. **Visual indicators**:
   - Clear focus states
   - Color not sole indicator (use icons + text)
   - High contrast mode support

---

## Testing Strategy

### Unit Tests

Test each detection function:
```javascript
describe('Pattern Detection', () => {
  test('detects Chinese names with CJK characters', () => {
    expect(detectNamePattern('习近平')).toMatchObject({
      pattern: 'chinese',
      confidence: 'high'
    });
  });

  test('detects Spanish double surnames', () => {
    expect(detectNamePattern('María García Rodríguez')).toMatchObject({
      pattern: 'spanish',
      confidence: 'medium'
    });
  });

  test('detects mononyms', () => {
    expect(detectNamePattern('Sukarno')).toMatchObject({
      pattern: 'mononym'
    });
  });
});
```

### Integration Tests

Test full user flows:
```javascript
describe('Name Input Flow', () => {
  test('user can enter Chinese name and add romanization', async () => {
    // 1. User enters Chinese characters
    await userTypes('习近平');
    
    // 2. System detects pattern
    expect(screen.getByText(/East Asian name/i)).toBeInTheDocument();
    
    // 3. User confirms
    await userClick('Yes, that\'s correct');
    
    // 4. Enhanced fields appear
    expect(screen.getByLabelText(/Pinyin/i)).toBeInTheDocument();
    
    // 5. User adds romanization
    await userTypes('Xi', { field: 'family.en' });
    await userTypes('Jinping', { field: 'given.en' });
    
    // 6. User selects display order
    await userClick('family_first');
    
    // 7. Preview updates
    expect(screen.getByText('Xi Jinping')).toBeInTheDocument();
  });
});
```

### User Acceptance Testing

Test with real users from different cultures:
- Chinese speakers: Can they input and romanize names correctly?
- Arabic speakers: RTL support working? Component detection accurate?
- Spanish speakers: Surname order intuitive? Drag-and-drop clear?
- Indonesian users: Mononym path straightforward?

---

## Localization (i18n)

### Supported Languages

Priority languages for UI translation:
1. English (default)
2. Spanish
3. Chinese (Simplified & Traditional)
4. Arabic
5. French
6. Portuguese

### Translation Keys

```json
{
  "name_input": {
    "title": "What should we call you?",
    "placeholder": "Enter your full name",
    "continue": "Continue",
    
    "detection": {
      "title": "We detected: {pattern}",
      "confirm": "Yes, that's correct",
      "choose_different": "No, let me choose a different format",
      "keep_simple": "Keep it simple - use as entered"
    },
    
    "patterns": {
      "chinese": "East Asian Name",
      "arabic": "Arabic Name",
      "spanish": "Spanish/Portuguese Name",
      "tamil": "South Indian Name",
      "mononym": "Single Name",
      "western": "Western/Standard Name"
    },
    
    "metadata": {
      "display_order": {
        "question": "How should your name be ordered in English?",
        "family_first": "Family name first",
        "given_first": "Given name first",
        "context_aware": "Automatic (adapt to context)"
      },
      
      "display_preference": {
        "question": "How should your name typically appear?",
        "formal_full": "Full formal",
        "formal_short": "Standard formal",
        "informal": "Informal",
        "kunya": "Honorific"
      }
    }
  }
}
```

---

## Future Enhancements

1. **Voice input**: Allow users to speak their name for automatic transcription
2. **Name pronunciation**: Record audio of how to pronounce the name
3. **Import from contacts**: Parse existing contact card data
4. **Bulk family input**: Easier setup for families with shared surname structures
5. **AI-assisted parsing**: More sophisticated name component detection
6. **Cultural context help**: In-app explanations of naming traditions
7. **Name change wizard**: Special flow for users updating their name (with deadname protection)

---

## Related Documentation

- [Backend Architecture - Cultural Naming Patterns](../../architecture/data-architecture.qmd#cultural-naming-pattern-examples)
- [Backend Architecture - Deadname Protection](../../architecture/security-architecture.qmd#deadname-protection)
- [API Specification - Name Structure Endpoints](./api-specification.md)
- [Accessibility Guidelines](./accessibility.md)
- [Localization Guide](./localization.md)

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2025-10-22 | 1.0 | Initial documentation created |

