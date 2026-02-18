/**
 * Unit tests for ScopeDisplay component.
 *
 * Tests verify scope list rendering, sensitive badges, checkbox behavior
 * in selectable mode, required scope handling, and expandable details.
 */

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ScopeDisplay from '@/components/oauth/ScopeDisplay.vue'
import type { OAuthScope } from '@/types'

// Mock vue-i18n
vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string) => key,
    locale: { value: 'en' }
  })
}))

// Stub heroicon components
const iconStubs = {
  CheckCircleIcon: { template: '<svg class="icon text-success" />' },
  ExclamationTriangleIcon: { template: '<svg class="icon text-warning" />' },
  ChevronDownIcon: { template: '<svg class="chevron-icon" />' },
  ChevronUpIcon: { template: '<svg class="chevron-icon" />' }
}

const mockScopes: OAuthScope[] = [
  { scope_name: 'openid', description: 'Basic identity', is_sensitive: false },
  { scope_name: 'profile:read:basic', description: 'Name and type', is_sensitive: false },
  { scope_name: 'contexts:legal:read', description: 'Legal context data', is_sensitive: true }
]

describe('ScopeDisplay', () => {
  const mountOptions = (props: Record<string, unknown> = {}) => ({
    props: { scopes: mockScopes, ...props },
    global: { stubs: iconStubs }
  })

  it('should render list of scopes with name and description', () => {
    const wrapper = mount(ScopeDisplay, mountOptions())

    const items = wrapper.findAll('.scope-item')
    expect(items).toHaveLength(3)
    expect(items[0].find('.scope-name').text()).toBe('openid')
    expect(items[0].find('.scope-description').text()).toBe('Basic identity')
  })

  it('should show warning icon for sensitive scopes', () => {
    const wrapper = mount(ScopeDisplay, mountOptions())

    const items = wrapper.findAll('.scope-item')
    // openid: not sensitive -> success icon
    expect(items[0].find('.text-success').exists()).toBe(true)
    // contexts:legal:read: sensitive -> warning icon
    expect(items[2].find('.text-warning').exists()).toBe(true)
  })

  it('should show sensitive badge for is_sensitive scopes', () => {
    const wrapper = mount(ScopeDisplay, mountOptions())

    const items = wrapper.findAll('.scope-item')
    expect(items[2].find('.badge-warning').exists()).toBe(true)
    expect(items[2].find('.badge-warning').text()).toBe('Sensitive')
  })

  it('should show checkboxes in selectable mode', () => {
    const wrapper = mount(ScopeDisplay, mountOptions({
      selectable: true,
      selectedScopes: ['openid', 'profile:read:basic']
    }))

    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    expect(checkboxes).toHaveLength(3)
  })

  it('should disable checkbox for required scopes (openid)', () => {
    const wrapper = mount(ScopeDisplay, mountOptions({
      selectable: true,
      selectedScopes: ['openid']
    }))

    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    expect(checkboxes[0].attributes('disabled')).toBeDefined()
    expect(checkboxes[1].attributes('disabled')).toBeUndefined()
  })

  it('should show required badge for openid scope', () => {
    const wrapper = mount(ScopeDisplay, mountOptions({
      selectable: true,
      selectedScopes: ['openid']
    }))

    expect(wrapper.find('.badge-primary').exists()).toBe(true)
    expect(wrapper.find('.badge-primary').text()).toBe('oauth.requiredScope')
  })

  it('should emit update:selectedScopes when non-required scope toggled', async () => {
    const wrapper = mount(ScopeDisplay, mountOptions({
      selectable: true,
      selectedScopes: ['openid', 'profile:read:basic']
    }))

    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    // Toggle profile:read:basic (index 1, non-required)
    await checkboxes[1].trigger('change')

    const emitted = wrapper.emitted('update:selectedScopes')
    expect(emitted).toBeTruthy()
    // Should remove profile:read:basic from selection
    expect(emitted![0][0]).toEqual(['openid'])
  })

  it('should not emit when required scope checkbox triggered', async () => {
    const wrapper = mount(ScopeDisplay, mountOptions({
      selectable: true,
      selectedScopes: ['openid']
    }))

    const checkboxes = wrapper.findAll('input[type="checkbox"]')
    await checkboxes[0].trigger('change')

    expect(wrapper.emitted('update:selectedScopes')).toBeUndefined()
  })

  it('should not show checkboxes when not in selectable mode', () => {
    const wrapper = mount(ScopeDisplay, mountOptions())

    expect(wrapper.findAll('input[type="checkbox"]')).toHaveLength(0)
  })

  it('should show expandable detail panel when expandable and clicked', async () => {
    const wrapper = mount(ScopeDisplay, mountOptions({
      expandable: true
    }))

    // Initially no detail panels
    expect(wrapper.find('.scope-detail').exists()).toBe(false)

    // Click expand for openid scope
    await wrapper.findAll('.scope-expand')[0].trigger('click')

    const detail = wrapper.find('.scope-detail')
    expect(detail.exists()).toBe(true)
    expect(detail.text()).toContain('User identifier (sub)')
  })
})
