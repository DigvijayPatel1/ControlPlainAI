import type { GuardrailCheckResult } from '../lib/api'

export type GuardStatus = 'idle' | 'checking' | 'pass' | 'mask' | 'review' | 'block' | 'error'

export interface GuardEvent {
    status: GuardStatus
    result?: GuardrailCheckResult
    error?: string
}

type Listener = (event: GuardEvent) => void

class GuardBus extends EventTarget {
    private listeners = new Set<Listener>()

    emit(event: GuardEvent) {
        this.listeners.forEach((listener) => listener(event))
    }

    subscribe(listener: Listener): () => void {
        this.listeners.add(listener)
        return () => this.listeners.delete(listener)
    }
}

export const guardBus = new GuardBus()
