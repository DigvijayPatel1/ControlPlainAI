class GuardBus extends EventTarget {
    listeners = new Set();
    emit(event) {
        this.listeners.forEach((listener) => listener(event));
    }
    subscribe(listener) {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }
}
export const guardBus = new GuardBus();
