export const getToken = () => localStorage.getItem("token");

export const setToken = (token) => {
  localStorage.setItem("token", token);
};

export const clearToken = () => {
  localStorage.removeItem("token");
  localStorage.removeItem("refreshToken");
};

export const isAuthed = () => Boolean(getToken());
