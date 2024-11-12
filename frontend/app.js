// frontend/app.js

// Registrazione del Service Worker
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/service-worker.js')
        .then(reg => {
            console.log('Service Worker registrato:', reg);
        })
        .catch(err => {
            console.log('Errore nella registrazione del Service Worker:', err);
        });
}

// Richiedere il permesso per le notifiche
if (Notification.permission !== "granted" && Notification.permission !== "denied") {
    Notification.requestPermission().then(permission => {
        if (permission === "granted") {
            console.log("Notifiche consentite");
        }
    });
}

// Gestione del download
document.getElementById('downloadButton').addEventListener('click', () => {
    const url = document.getElementById('videoUrl').value.trim();
    const quality = document.getElementById('videoQuality').value;
    const statusDiv = document.getElementById('status');

    if (!url) {
        statusDiv.innerHTML = '<div class="alert alert-danger">Inserisci un URL valido.</div>';
        return;
    }

    statusDiv.innerHTML = `
        <div class="alert alert-info d-flex align-items-center">
            <strong>Inizio del download...</strong>
            <div class="spinner-border ml-auto" role="status" aria-hidden="true"></div>
        </div>
    `;

    fetch('/download', {  // Backend URL relativo
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: url, quality: quality })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            statusDiv.innerHTML = `<div class="alert alert-danger">Errore: ${data.error}</div>`;
        } else {
            const downloadLink = `/download/${data.download_id}`;
            statusDiv.innerHTML = `
                <div class="alert alert-success">
                    Download completato!
                    <a href="${downloadLink}" class="btn btn-success btn-sm ml-3">Clicca qui per scaricare il video</a>
                </div>
            `;
            // Mostra la notifica
            if (Notification.permission === "granted") {
                new Notification("Download Completo", {
                    body: "Il tuo video è pronto per essere scaricato!",
                    icon: "/icons/icon-192x192.png"
                });
            }
        }
    })
    .catch(error => {
        console.error('Errore:', error);
        statusDiv.innerHTML = `<div class="alert alert-danger">Errore nel processo di download.</div>`;
    });
});
