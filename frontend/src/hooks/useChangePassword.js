import { useCallback, useState } from "react";

import { changePassword } from "../services/profileService";

export default function useChangePassword() {
  const [saving, setSaving] = useState(false);

  const submit = useCallback(async (payload) => {
    if (saving) return null;

    setSaving(true);
    try {
      return await changePassword(payload);
    } finally {
      setSaving(false);
    }
  }, [saving]);

  return { saving, submit };
}
