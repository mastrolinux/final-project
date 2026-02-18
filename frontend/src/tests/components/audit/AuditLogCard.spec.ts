/**
 * Unit tests for AuditLogCard component.
 *
 * Tests verify event type formatting, timestamp display,
 * operation badge mapping, and changes detail rendering.
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AuditLogCard from '@/components/audit/AuditLogCard.vue'

// Mock vue-i18n
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string) => key,
    d: (date: Date, format: string) => date.toISOString(),
    locale: { value: 'en' }
  })
}))

const baseEntry = {
  id: 'audit-1',
  event_type: 'auth.login.success',
  operation: 'login' as const,
  resource_type: 'auth_user',
  resource_id: '12345678-abcd-1234-5678-abcdef123456',
  created_at: '2026-02-18T10:00:00Z',
  ip_address: '192.168.1.1',
  user_agent: 'Mozilla/5.0',
  changes: null,
  previous_hash: null,
  entry_hash: 'abc123'
}

describe('AuditLogCard', () => {
  it('should render event type', () => {
    const wrapper = mount(AuditLogCard, {
      props: { entry: baseEntry }
    })

    // formatEventType replaces dots with ' > '
    expect(wrapper.text()).toContain('auth > login > success')
  })

  it('should render operation', () => {
    const wrapper = mount(AuditLogCard, {
      props: { entry: baseEntry }
    })

    expect(wrapper.text()).toContain('login')
  })

  it('should render timestamp', () => {
    const wrapper = mount(AuditLogCard, {
      props: { entry: baseEntry }
    })

    // formatTimestamp uses Date.toLocaleString
    expect(wrapper.text()).toContain('Feb')
  })

  it('should render truncated resource_id', () => {
    const wrapper = mount(AuditLogCard, {
      props: { entry: baseEntry }
    })

    // Should show at least part of the resource_id
    expect(wrapper.text()).toContain('12345678')
  })

  it('should show changes when present', () => {
    const entryWithChanges = {
      ...baseEntry,
      changes: { email: { old: 'old@test.com', new: 'new@test.com' } }
    }

    const wrapper = mount(AuditLogCard, {
      props: { entry: entryWithChanges }
    })

    expect(wrapper.text()).toContain('email')
  })

  it('should handle entry without changes', () => {
    const wrapper = mount(AuditLogCard, {
      props: { entry: { ...baseEntry, changes: null } }
    })

    // Should render without errors
    expect(wrapper.exists()).toBe(true)
  })
})
