import { useEffect, useState } from "react";
import { fetchRuntimeConfig, RuntimeConfig } from "../lib/api";

// Small shared hook so we don't duplicate runtime config logic.
// We default to { readOnly: false } because you're now full prod.
export function useRuntimeConfig() {
  const [config, setConfig] = useState<RuntimeConfig>({ readOnly: false });
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const data = await fetchRuntimeConfig();
        if (!ignore) {
          setConfig(data);
        }
      } catch {
        // swallow; default is already readOnly:false
      } finally {
        if (!ignore) {
          setLoaded(true);
        }
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, []);

  return { config, loaded };
}
