<script setup lang="ts">
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'

defineProps<{
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
    <Dialog as="div" class="modal-dialog" @close="handleClose">
      <TransitionChild
        as="template"
        enter="ease-out duration-300"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="ease-in duration-200"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="modal-backdrop" />
      </TransitionChild>

      <div class="modal-scroll-container">
        <div class="modal-layout">
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
              class="modal-panel"
              :class="maxWidth || 'modal-panel-default'"
            >
              <div class="modal-header">
                <div class="modal-header-layout">
                  <div class="modal-content">
                    <DialogTitle v-if="title" as="h3" class="modal-title">
                      {{ title }}
                    </DialogTitle>
                    <div class="modal-body">
                      <slot />
                    </div>
                  </div>
                </div>
              </div>
              <div v-if="$slots.footer" class="modal-footer">
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
.modal-dialog {
  position: relative;
  z-index: var(--z-modal);
}

.modal-backdrop {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  background-color: var(--color-gray-500);
  opacity: 0.75;
  transition-property: opacity;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 150ms;
}

.modal-scroll-container {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 10;
  overflow-y: auto;
}

.modal-layout {
  display: flex;
  min-height: 100%;
  align-items: flex-end;
  justify-content: center;
  padding: var(--spacing-4);
  text-align: center;
}

.modal-panel {
  position: relative;
  overflow: hidden;
  border-radius: var(--radius-lg);
  background-color: var(--bg-secondary);
  text-align: left;
  box-shadow: var(--shadow-xl);
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 150ms;
}

.modal-header {
  background-color: var(--bg-secondary);
  padding: var(--spacing-5) var(--spacing-4) var(--spacing-4);
}

.modal-header-layout {
  /* Stacked on mobile, flex on sm+ */
}

.modal-content {
  margin-top: var(--spacing-3);
  text-align: center;
  width: 100%;
}

.modal-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  line-height: 1.5rem;
  color: var(--text-primary);
  margin-bottom: var(--spacing-4);
}

.modal-body {
  margin-top: var(--spacing-2);
}

.modal-footer {
  background-color: var(--bg-tertiary);
  padding: var(--spacing-3) var(--spacing-4);
}

/* Responsive: sm (640px+) */
@media (min-width: 640px) {
  .modal-layout {
    align-items: center;
    padding: 0;
  }

  .modal-panel {
    margin-top: var(--spacing-8);
    margin-bottom: var(--spacing-8);
    width: 100%;
  }

  .modal-panel-default {
    max-width: 32rem;
  }

  .modal-header {
    padding: var(--spacing-6);
    padding-bottom: var(--spacing-4);
  }

  .modal-header-layout {
    display: flex;
    align-items: flex-start;
  }

  .modal-content {
    margin-left: var(--spacing-4);
    margin-top: 0;
    text-align: left;
  }

  .modal-footer {
    display: flex;
    flex-direction: row-reverse;
    padding-left: var(--spacing-6);
    padding-right: var(--spacing-6);
  }
}
</style>
