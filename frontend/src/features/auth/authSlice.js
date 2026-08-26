import { createSlice } from '@reduxjs/toolkit';
const initialState = {
    token: localStorage.getItem('cp_token'),
    user: JSON.parse(localStorage.getItem('cp_user') ?? 'null'),
    pendingApiKey: null,
};
const authSlice = createSlice({
    name: 'auth',
    initialState,
    reducers: {
        credentialsReceived: (state, action) => {
            state.token = action.payload.token;
            state.user = action.payload.user;
            state.pendingApiKey = action.payload.apiKey ?? null;
            localStorage.setItem('cp_token', action.payload.token);
            localStorage.setItem('cp_user', JSON.stringify(action.payload.user));
        },
        apiKeyIssued: (state, action) => {
            state.pendingApiKey = action.payload;
        },
        apiKeyAcknowledged: (state) => {
            state.pendingApiKey = null;
        },
        loggedOut: (state) => {
            state.token = null;
            state.user = null;
            state.pendingApiKey = null;
            localStorage.removeItem('cp_token');
            localStorage.removeItem('cp_user');
        },
    },
});
export const { credentialsReceived, apiKeyIssued, apiKeyAcknowledged, loggedOut } = authSlice.actions;
export default authSlice.reducer;
