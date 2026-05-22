import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { getOrganizations } from "../api/organizations";

export const OrganizationContext = createContext(null);

export function OrganizationProvider({ children }) {
  const [organizations, setOrganizations] = useState([]);
  const [activeOrganization, setActiveOrganizationState] = useState(null);
  const [loadingOrganizations, setLoadingOrganizations] = useState(false);

  const emitOrganizationChange = (organizationId) => {
    window.dispatchEvent(
      new CustomEvent("organization:changed", {
        detail: { organizationId },
      })
    );
  };

  const changeOrganization = (org) => {
    setActiveOrganizationState(org);

    if (org?.id) {
      localStorage.setItem("active_organization_id", String(org.id));
      emitOrganizationChange(String(org.id));
    } else {
      localStorage.removeItem("active_organization_id");
      emitOrganizationChange(null);
    }
  };

  const refreshOrganizations = useCallback(async () => {
    setLoadingOrganizations(true);

    try {
      const data = await getOrganizations();
      setOrganizations(data);

      const savedId = localStorage.getItem("active_organization_id");
      const savedOrg = data.find(
        (org) => String(org.id) === String(savedId)
      );

      const selected = savedOrg || data[0] || null;

      setActiveOrganizationState(selected);

      if (selected?.id) {
        localStorage.setItem("active_organization_id", String(selected.id));
        emitOrganizationChange(String(selected.id));
      } else {
        emitOrganizationChange(null);
      }
    } catch (err) {
      if (process.env.NODE_ENV !== "production") {
        console.error("Failed to load organizations", err?.friendlyMessage || err?.message);
      }
    } finally {
      setLoadingOrganizations(false);
    }
  }, []);

  useEffect(() => {
    if (localStorage.getItem("access")) {
      refreshOrganizations();
    }
  }, [refreshOrganizations]);

  return (
    <OrganizationContext.Provider
      value={{
        organizations,
        activeOrganization,
        changeOrganization,
        refreshOrganizations,
        loadingOrganizations,
      }}
    >
      {children}
    </OrganizationContext.Provider>
  );
}

export function useOrganization() {
  return useContext(OrganizationContext);
}
