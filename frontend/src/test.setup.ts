// Ensure localStorage is properly available in jsdom
if (!window.localStorage || typeof window.localStorage.clear !== "function") {
  const store: Record<string, string> = {};

  Object.defineProperty(window, "localStorage", {
    value: {
      getItem: (key: string) => store[key] || null,
      setItem: (key: string, value: string) => {
        store[key] = value.toString();
      },
      removeItem: (key: string) => {
        delete store[key];
      },
      clear: () => {
        Object.keys(store).forEach((key) => {
          delete store[key];
        });
      },
      key: (index: number) => {
        const keys = Object.keys(store);
        return keys[index] || null;
      },
      get length() {
        return Object.keys(store).length;
      },
    },
    configurable: true,
  });
}
