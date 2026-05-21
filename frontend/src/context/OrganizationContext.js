import { createContext, useContext, useEffect, useState } from "react";
import { getOrganizations } from "../api/organizations";

export const OrganizationContext = createContext(null);

export function OrganizationProvider({ children }) {
  const [organizations, setOrganizations] = useState([]);
  const [activeOrganization, setActiveOrganizationState] = useState(null);
  const [loadingOrganizations, setLoadingOrganizations] = useState(false);

  const changeOrganization = (org) => {
    setActiveOrganizationState(org);

    if (org?.id) {
      localStorage.setItem("active_organization_id", String(org.id));
    } else {
      localStorage.removeItem("active_organization_id");
    }
  };

  const refreshOrganizations = async () => {
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
      }
    } catch (err) {
      console.error("Failed to load organizations", err);
    } finally {
      setLoadingOrganizations(false);
    }
  };

  useEffect(() => {
    if (localStorage.getItem("access")) {
      refreshOrganizations();
    }
  }, []);

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