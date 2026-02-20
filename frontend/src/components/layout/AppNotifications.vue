<script setup lang="ts">
import { useUiStore, type Notification } from "@/stores";

const uiStore = useUiStore();

function getNotificationClass(type: Notification["type"]): string {
  return `notification notification-${type}`;
}

function handleClose(id: string) {
  uiStore.removeNotification(id);
}
</script>

<template>
  <div class="notifications-container" aria-live="polite">
    <TransitionGroup name="notification">
      <div
        v-for="notification in uiStore.notifications"
        :key="notification.id"
        :class="getNotificationClass(notification.type)"
        role="alert"
      >
        <span class="notification-message">{{ notification.message }}</span>
        <button
          class="notification-close"
          @click="handleClose(notification.id)"
          aria-label="Close notification"
        >
          &times;
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.notifications-container {
  position: fixed;
  top: calc(var(--header-height) + var(--spacing-4));
  right: var(--spacing-4);
  z-index: var(--z-toast);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  max-width: 400px;
  width: 100%;
  pointer-events: none;
}

.notification {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-3);
  padding: var(--spacing-3) var(--spacing-4);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  pointer-events: auto;
}

.notification-success {
  background-color: var(--color-success-50);
  border: 1px solid var(--color-success-500);
  color: var(--color-success-700);
}

.notification-error {
  background-color: var(--color-error-50);
  border: 1px solid var(--color-error-500);
  color: var(--color-error-700);
}

.notification-warning {
  background-color: var(--color-warning-50);
  border: 1px solid var(--color-warning-500);
  color: var(--color-warning-700);
}

.notification-info {
  background-color: var(--color-info-50);
  border: 1px solid var(--color-info-500);
  color: var(--color-info-700);
}

.notification-message {
  flex: 1;
  font-size: var(--font-size-sm);
}

.notification-close {
  flex-shrink: 0;
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-lg);
  line-height: 1;
  opacity: 0.7;
  cursor: pointer;
  background: none;
  border: none;
  color: inherit;
}

.notification-close:hover {
  opacity: 1;
}

/* Transition animations */
.notification-enter-active,
.notification-leave-active {
  transition: all var(--transition-normal);
}

.notification-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.notification-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.notification-move {
  transition: transform var(--transition-normal);
}

@media (max-width: 480px) {
  .notifications-container {
    left: var(--spacing-4);
    right: var(--spacing-4);
    max-width: none;
  }
}
</style>
