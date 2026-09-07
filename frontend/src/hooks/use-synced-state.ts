"use client";

import { useState } from "react";

/**
 * Local editable state that stays in sync with an external value (e.g. URL
 * state) without an effect. Follows the "adjusting state when a prop
 * changes" pattern from the React docs — comparing during render and
 * calling `setState` conditionally in the render body — instead of
 * `useEffect(() => setState(external), [external])`, which the
 * `react-hooks/set-state-in-effect` rule flags because it forces an extra
 * commit/paint cycle.
 *
 * Used for debounced filter inputs: local edits are allowed to diverge
 * from `externalValue` while typing, but external changes (browser
 * back/forward, a "clear filters" action) still overwrite the draft.
 */
export function useSyncedState<T>(
  externalValue: T,
): [T, React.Dispatch<React.SetStateAction<T>>] {
  const [value, setValue] = useState(externalValue);
  const [prevExternal, setPrevExternal] = useState(externalValue);

  if (externalValue !== prevExternal) {
    setPrevExternal(externalValue);
    setValue(externalValue);
  }

  return [value, setValue];
}
