import { create } from 'zustand'
import { EncounterAPI } from '../api/client'

export const useCaseStore = create((set, get) => ({
    pendingCount: 0,
    lastUpdate: null,

    fetchCounts: async (userId, role) => {
        if (!userId || role !== 'doctor') return;
        try {
            // Fetch only assigned encounters for this doctor
            const encounters = await EncounterAPI.list({ 
                status: 'assigned',
                assigned_doctor: userId
            })
            const count = Array.isArray(encounters) ? encounters.length : 0
            set({ pendingCount: count, lastUpdate: new Date() })
        } catch (error) {
            console.error("[useCaseStore] Error fetching counts:", error)
        }
    },

    setPendingCount: (count) => set({ pendingCount: count })
}))
