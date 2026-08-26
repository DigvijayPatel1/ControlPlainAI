import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'

export type UserRole = 'user' | 'reviewer' | 'admin'

export interface AuthUser {
    id: string
    email: string
    full_name: string
    role: UserRole
    is_active: boolean
    default_principal_id: string | null
    created_at: string
}

export interface IssuedApiKey {
    principal_id: string
    raw_key: string
}

interface AuthState {
    token: string | null
    user: AuthUser | null
    /** Raw API key, only ever populated right after register/rotate. Never re-fetchable. */
    pendingApiKey: IssuedApiKey | null
}

const initialState: AuthState = {
    token: localStorage.getItem('cp_token'),
    user: JSON.parse(localStorage.getItem('cp_user') ?? 'null'),
    pendingApiKey: null,
}

const authSlice = createSlice({
    name: 'auth',
    initialState,
    reducers: {
        credentialsReceived: (
            state,
            action: PayloadAction<{ token: string; user: AuthUser; apiKey?: IssuedApiKey }>,
        ) => {
            state.token = action.payload.token
            state.user = action.payload.user
            state.pendingApiKey = action.payload.apiKey ?? null
            localStorage.setItem('cp_token', action.payload.token)
            localStorage.setItem('cp_user', JSON.stringify(action.payload.user))
        },
        apiKeyIssued: (state, action: PayloadAction<IssuedApiKey>) => {
            state.pendingApiKey = action.payload
        },
        apiKeyAcknowledged: (state) => {
            state.pendingApiKey = null
        },
        loggedOut: (state) => {
            state.token = null
            state.user = null
            state.pendingApiKey = null
            localStorage.removeItem('cp_token')
            localStorage.removeItem('cp_user')
        },
    },
})

export const { credentialsReceived, apiKeyIssued, apiKeyAcknowledged, loggedOut } = authSlice.actions
export default authSlice.reducer
