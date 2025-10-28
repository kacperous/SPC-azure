        // --- INICJALIZACJA PAMIĘCI ---
        let accessToken = localStorage.getItem('access_token');
        let refreshToken = localStorage.getItem('refresh_token');
        let currentUsername = '';
        let isAdmin = false;
        
        // --- NARZĘDZIA OGÓLNE ---
        function getAuthHeaders(contentType = 'application/json') {
            const headers = { 'Authorization': `Bearer ${accessToken}` };
            if (contentType) {
                headers['Content-Type'] = contentType;
            }
            return headers;
        }

        function decodeToken(token) {
            const payload = JSON.parse(atob(token.split('.')[1]));
            currentUsername = payload.username;
            // Wymaga, by backend dodawał is_staff i is_superuser
            isAdmin = payload.is_staff || payload.is_superuser || false; 
        }
        
        // Funkcja przełączająca widoki (serce interfejsu)
        function toggleView(isLoggedIn) {
            document.getElementById('auth-screen').classList.toggle('d-none', isLoggedIn);
            
            // Pokaż pulpit
            const dashboard = document.getElementById('dashboard-screen');
            dashboard.classList.toggle('d-none', !isLoggedIn);
            
            document.getElementById('logout-btn').classList.toggle('d-none', !isLoggedIn);
            document.getElementById('username-display').classList.toggle('d-none', !isLoggedIn);

            if (isLoggedIn) {
                document.getElementById('username-display').textContent = `Witaj, ${currentUsername}! ${isAdmin ? '(ADMIN)' : ''}`;
                
                // Kluczowa logika: Pokaż kontrolki admina tylko, gdy zalogowany jest admin
                document.getElementById('admin-dashboard').classList.toggle('d-none', !isAdmin);

                loadFiles();
            } else {
                currentUsername = '';
                isAdmin = false;
                document.getElementById('username-display').textContent = '';
            }
        }
        
        // --- LOGIKA UWIERZYTELNIANIA I JWT ---

        async function login() {
            const data = {
                username: document.getElementById('login-username').value,
                password: document.getElementById('login-password').value
            };
            const errorElement = document.getElementById('login-error');
            errorElement.textContent = '';

            try {
                const response = await fetch('/api/users/token/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    const tokenData = await response.json();
                    accessToken = tokenData.access;
                    refreshToken = tokenData.refresh;

                    localStorage.setItem('access_token', accessToken);
                    localStorage.setItem('refresh_token', refreshToken);
                    
                    decodeToken(accessToken);
                    toggleView(true); // Przełącz na pulpit
                } else {
                    errorElement.textContent = 'Błędny login lub hasło!';
                }
            } catch (error) {
                errorElement.textContent = 'Błąd połączenia z serwerem.';
            }
        }

        async function registerUser() {
            const data = {
                username: document.getElementById('reg-username').value,
                email: document.getElementById('reg-email').value,
                password: document.getElementById('reg-password').value,
            };
            const errorElement = document.getElementById('register-error');
            errorElement.textContent = '';
            document.getElementById('register-success').textContent = '';

            try {
                const response = await fetch('/api/users/register/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (response.status === 201) {
                    document.getElementById('register-success').textContent = 'Rejestracja udana! Możesz się zalogować.';
                    new bootstrap.Tab(document.getElementById('login-tab')).show(); 
                } else {
                    const errorData = await response.json();
                    errorElement.textContent = 'Błąd rejestracji: ' + JSON.stringify(errorData);
                }
            } catch (error) {
                errorElement.textContent = 'Błąd połączenia z serwerem.';
            }
        }

        function logout() {
            accessToken = null;
            refreshToken = null;
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            toggleView(false);
        }

        async function refreshAccessToken() {
            if (!refreshToken) return false;
            try {
                const response = await fetch('/api/users/token/refresh/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ refresh: refreshToken })
                });
                
                if (response.ok) {
                    const tokenData = await response.json();
                    accessToken = tokenData.access;
                    localStorage.setItem('access_token', accessToken);
                    decodeToken(accessToken);
                    return true;
                }
            } catch (e) {
                console.error("Błąd odświeżania tokenu:", e);
            }
            return false;
        }

        // --- LOGIKA PLIKÓW (CRUD) ---

        async function loadFiles() {
            if (!accessToken) return toggleView(false);

            // Zabezpieczenie przed błędem DOM
            const listElement = document.getElementById('file-list');
            const loadingElement = document.getElementById('loading-files');
            const noFilesElement = document.getElementById('no-files-msg');
            
            if (!listElement || !loadingElement || !noFilesElement) {
                console.error("Krytyczny błąd DOM: Nie znaleziono kluczowych kontenerów. Przerwano ładowanie.");
                return; 
            }

            const sortValue = document.getElementById('sort-select').value;
            const userFilter = document.getElementById('user-filter').value;
            
            let url = '/api/files/';
            let params = [];
            
            if (isAdmin) {
                params.push('all_files=true'); 
                
                if (userFilter) {
                    params.push(`owner_username=${userFilter}`);
                    document.getElementById('files-owner-info').textContent = `Użytkownika: ${userFilter}`;
                } else {
                    document.getElementById('files-owner-info').textContent = `WSZYSTKICH UŻYTKOWNIKÓW`;
                }
            } else {
                document.getElementById('files-owner-info').textContent = `Twoje`;
            }
            
            params.push(`ordering=${sortValue}`);
            
            if (params.length > 0) {
                url += '?' + params.join('&');
            }

            listElement.innerHTML = '';
            loadingElement.classList.remove('d-none');
            noFilesElement.classList.add('d-none');

            try {
                const response = await fetch(url, {
                    method: 'GET',
                    headers: getAuthHeaders()
                });

                if (response.status === 401) {
                    if (await refreshAccessToken()) return loadFiles();
                    return toggleView(false);
                }

                const files = await response.json();
                loadingElement.classList.add('d-none');
                listElement.innerHTML = '';

                if (files.length === 0) {
                    noFilesElement.classList.remove('d-none');
                } else {
                    files.forEach(file => {
                        const ownerInfo = (isAdmin) 
                            ? `<span class="badge bg-primary me-2">${file.owner}</span>` : '';
                        
                        const fileSizeKB = (file.file_size / 1024).toFixed(2);

                        listElement.innerHTML += `
                            <li class="list-group-item d-flex justify-content-between align-items-center file-list-item">
                                <span class="d-flex align-items-center">
                                    ${ownerInfo}
                                    ${file.original_filename} (${fileSizeKB} KB, ID: ${file.id})
                                </span>
                                <div>
                                    <button class="btn btn-sm btn-secondary btn-action" onclick="viewFile(${file.id})">Zobacz</button>
                                    <button class="btn btn-sm btn-info btn-action" onclick="downloadFile(${file.id})">Pobierz</button>
                                    <button class="btn btn-sm btn-danger btn-action" onclick="deleteFile(${file.id})">Usuń</button>
                                </div>
                            </li>
                        `;
                    });
                }

            } catch (error) {
                loadingElement.classList.add('d-none');
                listElement.innerHTML = '<li class="list-group-item text-danger">Błąd ładowania danych.</li>';
            }
        }

        async function uploadFile() {
            if (!accessToken) return;

            const fileInput = document.getElementById('file-input');
            const uploadStatus = document.getElementById('upload-status');
            const file = fileInput.files[0];
            
            if (!file) {
                uploadStatus.textContent = 'Wybierz plik do wgrania.';
                uploadStatus.classList.add('text-danger');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            uploadStatus.textContent = 'Wgrywanie...';
            uploadStatus.classList.remove('text-danger');
            uploadStatus.classList.add('text-warning');

            try {
                const response = await fetch('/api/files/', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    body: formData
                });

                if (response.status === 401) {
                    if (await refreshAccessToken()) return uploadFile();
                    return toggleView(false);
                }

                if (response.status === 201) {
                    uploadStatus.textContent = `Plik "${file.name}" wgrano pomyślnie!`;
                    uploadStatus.classList.remove('text-warning');
                    uploadStatus.classList.add('text-success');
                    fileInput.value = ''; // Czyść pole
                    loadFiles(); // Odśwież listę
                } else {
                    const errorData = await response.json();
                    uploadStatus.textContent = 'Błąd wgrywania: ' + JSON.stringify(errorData);
                    uploadStatus.classList.add('text-danger');
                }

            } catch (error) {
                uploadStatus.textContent = 'Błąd połączenia z API.';
                uploadStatus.classList.add('text-danger');
                console.error('Błąd wgrywania:', error);
            }
        }

        // --- AKCJE PLIKÓW ---
        
        // 1. ZOBACZ (Przekierowanie, które serwer obsłuży jako podgląd)
        async function viewFile(fileId) {
            if (!accessToken) return;

            try {
                const response = await fetch(`/api/files/${fileId}/view/`, {
                    method: 'GET',
                    headers: getAuthHeaders()
                });

                if (response.status === 401) {
                    if (await refreshAccessToken()) return viewFile(fileId);
                    return toggleView(false);
                }

                if (response.ok) {
                    const data = await response.json();
                    // Serwer zwraca link SAS, który otwiera podgląd (inline)
                    if (data.url) {
                        window.open(data.url, '_blank');
                    }
                } else if (response.status === 403) {
                    alert('Nie masz uprawnień do tego pliku.');
                } else {
                    alert('Błąd podczas otwierania pliku.');
                }
            } catch (error) {
                console.error('Błąd podglądu pliku:', error);
            }
        }

        // 2. POBIERZ (Przekierowanie, które serwer obsłuży jako wymuszenie zapisu)
        async function downloadFile(fileId) {
            if (!accessToken) return;

            try {
                const response = await fetch(`/api/files/${fileId}/download/`, {
                    method: 'GET',
                    headers: getAuthHeaders()
                });

                if (response.status === 401) {
                    if (await refreshAccessToken()) return downloadFile(fileId);
                    return logout();
                }

                if (response.ok) {
                    const data = await response.json();
                    if (data.url) {
                        // Serwer zwraca link SAS z Content-Disposition: attachment, który pobiera plik
                        window.open(data.url, '_blank');
                    }
                } else if (response.status === 403) {
                    alert('Nie masz uprawnień do tego pliku.');
                } else {
                    alert('Błąd podczas pobierania pliku.');
                }
            } catch (error) {
                console.error('Błąd pobierania pliku:', error);
            }
        }

        async function deleteFile(fileId) {
            if (!accessToken) return;
            if (!confirm(`Czy na pewno usunąć plik o ID ${fileId}?`)) return;
            
            try {
                const response = await fetch(`/api/files/${fileId}/`, {
                    method: 'DELETE',
                    headers: getAuthHeaders(null)
                });

                if (response.status === 401) {
                    if (await refreshAccessToken()) return deleteFile(fileId);
                    return toggleView(false);
                }

                if (response.status === 204) { 
                    loadFiles(); // Odśwież listę
                } else if (response.status === 403) {
                     alert('Brak uprawnień do usunięcia tego pliku.');
                } else {
                    alert('Błąd usuwania pliku!');
                }
            } catch (error) {
                console.error('Błąd usuwania:', error);
                alert('Wystąpił błąd podczas usuwania pliku.');
            }
        }


        // --- INICJALIZACJA APLIKACJI ---
        document.addEventListener('DOMContentLoaded', () => {
            if (accessToken) {
                try {
                    const payload = JSON.parse(atob(accessToken.split('.')[1]));
                    const now = Math.floor(Date.now() / 1000);
                    
                    if (payload.exp < now) {
                        refreshAccessToken().then(success => {
                            if (success) {
                                toggleView(true);
                            } else {
                                logout();
                            }
                        });
                    } else {
                        decodeToken(accessToken);
                        toggleView(true);
                    }
                } catch (e) {
                    logout(); 
                }
            } else {
                toggleView(false);
            }
        });