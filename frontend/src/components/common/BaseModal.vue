<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'

const props = defineProps<{
  isOpen: boolean
  title?: string
  maxWidth?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const handleClose = () => {
  emit('close')
}
</script>

<template>
  <TransitionRoot as="template" :show="isOpen">
    <Dialog as="div" class="relative z-modal" @close="handleClose">
      <TransitionChild
        as="template"
        enter="ease-out duration-300"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="ease-in duration-200"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
      </TransitionChild>

      <div class="fixed inset-0 z-10 overflow-y-auto">
        <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <TransitionChild
            as="template"
            enter="ease-out duration-300"
            enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            enter-to="opacity-100 translate-y-0 sm:scale-100"
            leave="ease-in duration-200"
            leave-from="opacity-100 translate-y-0 sm:scale-100"
            leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
          >
            <DialogPanel
              class="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full"
              :class="maxWidth || 'sm:max-w-lg'"
            >
              <div class="bg-white px-4 pb-4 pt-5 sm:p-6 sm:pb-4">
                <div class="sm:flex sm:items-start">
                  <div class="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left w-full">
                    <DialogTitle v-if="title" as="h3" class="text-base font-semibold leading-6 text-gray-900 mb-4">
                      {{ title }}
                    </DialogTitle>
                    <div class="mt-2">
                      <slot />
                    </div>
                  </div>
                </div>
              </div>
              <div v-if="$slots.footer" class="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6">
                <slot name="footer" />
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<style scoped>
/* Tailwind classes are used here assuming Tailwind is configured.
   If not, we would need to replace them with custom CSS.
   Given the project structure, it seems we are using custom CSS variables.
   I will replace Tailwind classes with custom CSS in a subsequent step if needed,
   but for now I'll stick to the Headless UI example structure and adapt it.
*/

.z-modal {
  z-index: var(--z-modal);
}

.fixed {
  position: fixed;
}

.inset-0 {
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
}

.bg-gray-500 {
  background-color: var(--color-gray-500);
}

.bg-opacity-75 {
  opacity: 0.75;
}

.transition-opacity {
  transition-property: opacity;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 150ms;
}

.overflow-y-auto {
  overflow-y: auto;
}

.flex {
  display: flex;
}

.min-h-full {
  min-height: 100%;
}

.items-end {
  align-items: flex-end;
}

.justify-center {
  justify-content: center;
}

.p-4 {
  padding: var(--spacing-4);
}

.text-center {
  text-align: center;
}

.relative {
  position: relative;
}

.transform {
  transform: translate(var(--tw-translate-x), var(--tw-translate-y)) rotate(var(--tw-rotate)) skewX(var(--tw-skew-x)) skewY(var(--tw-skew-y)) scaleX(var(--tw-scale-x)) scaleY(var(--tw-scale-y));
}

.overflow-hidden {
  overflow: hidden;
}

.rounded-lg {
  border-radius: var(--radius-lg);
}

.bg-white {
  background-color: white;
}

.text-left {
  text-align: left;
}

.shadow-xl {
  box-shadow: var(--shadow-xl);
}

.transition-all {
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 150ms;
}

.bg-gray-50 {
  background-color: var(--color-gray-50);
}

.px-4 {
  padding-left: var(--spacing-4);
  padding-right: var(--spacing-4);
}

.py-3 {
  padding-top: var(--spacing-3);
  padding-bottom: var(--spacing-3);
}

.pb-4 {
  padding-bottom: var(--spacing-4);
}

.pt-5 {
  padding-top: var(--spacing-5);
}

.mt-3 {
  margin-top: var(--spacing-3);
}

.mt-2 {
  margin-top: var(--spacing-2);
}

.mb-4 {
  margin-bottom: var(--spacing-4);
}

.text-base {
  font-size: var(--font-size-base);
}

.font-semibold {
  font-weight: var(--font-weight-semibold);
}

.leading-6 {
  line-height: 1.5rem;
}

.text-gray-900 {
  color: var(--color-gray-900);
}

.w-full {
  width: 100%;
}

@media (min-width: 640px) {
  .sm\:items-center {
    align-items: center;
  }
  .sm\:p-0 {
    padding: 0;
  }
  .sm\:my-8 {
    margin-top: 2rem;
    margin-bottom: 2rem;
  }
  .sm\:w-full {
    width: 100%;
  }
  .sm\:max-w-lg {
    max-width: 32rem;
  }
  .sm\:p-6 {
    padding: var(--spacing-6);
  }
  .sm\:pb-4 {
    padding-bottom: var(--spacing-4);
  }
  .sm\:flex {
    display: flex;
  }
  .sm\:items-start {
    align-items: flex-start;
  }
  .sm\:ml-4 {
    margin-left: var(--spacing-4);
  }
  .sm\:mt-0 {
    margin-top: 0;
  }
  .sm\:text-left {
    text-align: left;
  }
  .sm\:flex-row-reverse {
    flex-direction: row-reverse;
  }
  .sm\:px-6 {
    padding-left: var(--spacing-6);
    padding-right: var(--spacing-6);
  }
}
</style>
