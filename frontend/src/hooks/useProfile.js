import { useCallback, useEffect, useState } from "react";

import {
  getMemberships,
  getProfile,
  updateProfile,
  updateProfileAvatar,
} from "../services/profileService";

export default function useProfile() {
  const [profile, setProfile] = useState(null);
  const [memberships, setMemberships] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [profileData, membershipData] = await Promise.all([
        getProfile(),
        getMemberships(),
      ]);

      setProfile(profileData);
      setMemberships(membershipData);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const saveProfile = useCallback(async (payload) => {
    const updated = await updateProfile(payload);
    setProfile(updated);
    return updated;
  }, []);

  const saveAvatar = useCallback(async (file) => {
    const updated = await updateProfileAvatar(file);
    setProfile(updated);
    return updated;
  }, []);

  return {
    profile,
    memberships,
    loading,
    error,
    reload,
    saveProfile,
    saveAvatar,
  };
}
