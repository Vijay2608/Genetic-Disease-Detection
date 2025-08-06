function getStarted() {
  window.location.href = "/login"; // Update to your actual route
}
  async function uploadCSV() {
    const input = document.getElementById('fileInput');
    const message = document.getElementById('message');
    const dataPreview = document.getElementById('dataPreview');

    if (!input.files.length) {
      message.textContent = 'Please select a CSV file first.';
      return;
    }

    const file = input.files[0];
    const formData = new FormData();
    formData.append('file', file);

    Papa.parse(file, {
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: function(results) {
        const data = results.data;
        if (data.length === 0) return;
        let html = '<table><thead><tr>';
        Object.keys(data[0]).forEach(key => {
          html += `<th>${key}</th>`;
        });
        html += '</tr></thead><tbody>';
        data.slice(0, 10).forEach(row => {
          html += '<tr>';
          Object.values(row).forEach(val => {
            html += `<td>${val}</td>`;
          });
          html += '</tr>';
        });
        html += '</tbody></table>';
        dataPreview.innerHTML = html;
        dataPreview.style.display = 'block';
      }
    });

    try {
      const response = await fetch('/upload-dataset', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();
      message.textContent = result.message || 'Upload complete.';
    } catch (err) {
      message.textContent = 'Upload failed.';
      console.error(err);
    }
  }

  function clearTable() {
    const dataPreview = document.getElementById('dataPreview');
    const message = document.getElementById('message');
    dataPreview.innerHTML = '';
    dataPreview.style.display = 'none';
    message.textContent = '';
    document.getElementById('fileInput').value = '';
  }
   function renderTableFromData(data) {
    const dataPreview = document.getElementById('dataPreview');
    if (data.length === 0) return;

    let html = '<table><thead><tr>';
    Object.keys(data[0]).forEach(key => {
      html += `<th>${key}</th>`;
    });
    html += '</tr></thead><tbody>';
    data.slice(0, 10).forEach(row => {
      html += '<tr>';
      Object.values(row).forEach(val => {
        html += `<td>${val}</td>`;
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
    dataPreview.innerHTML = html;
    dataPreview.style.display = 'block';
  }

  async function uploadCSV() {
    const input = document.getElementById('fileInput');
    const message = document.getElementById('message');
    const dataPreview = document.getElementById('dataPreview');

    if (!input.files.length) {
      message.textContent = 'Please select a CSV file first.';
      return;
    }

    const file = input.files[0];
    const formData = new FormData();
    formData.append('file', file);

    Papa.parse(file, {
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: function(results) {
        const data = results.data;
        renderTableFromData(data);
        // Store parsed data in localStorage
        localStorage.setItem('csvPreviewData', JSON.stringify(data));
      }
    });

    try {
      const response = await fetch('/upload-dataset', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();
      message.textContent = result.message || 'Upload complete.';
    } catch (err) {
      message.textContent = 'Upload failed.';
      console.error(err);
    }
  }

  function clearTable() {
    const dataPreview = document.getElementById('dataPreview');
    const message = document.getElementById('message');
    const fileInput = document.getElementById('fileInput');

    dataPreview.innerHTML = '';
    dataPreview.style.display = 'none';
    message.textContent = '';
    fileInput.value = '';

    // Remove from localStorage
    localStorage.removeItem('csvPreviewData');
  }

  // On page load: check localStorage and render
  window.addEventListener('DOMContentLoaded', () => {
    const savedData = localStorage.getItem('csvPreviewData');
    if (savedData) {
      try {
        const parsed = JSON.parse(savedData);
        renderTableFromData(parsed);
      } catch (e) {
        console.error('Failed to load table from storage:', e);
        localStorage.removeItem('csvPreviewData');
      }
    }
  });
