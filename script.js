// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ Script loaded successfully');
    
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const loading = document.getElementById('loading');
    const errorMsg = document.getElementById('errorMsg');
    const resultSection = document.getElementById('resultSection');
    const resultCards = document.getElementById('resultCards');
    const downloadJson = document.getElementById('downloadJson');

    // Check if all elements exist
    if (!fileInput || !uploadBtn || !loading || !errorMsg || !resultSection || !resultCards || !downloadJson) {
        console.error('❌ Some HTML elements are missing!');
        console.log('fileInput:', fileInput);
        console.log('uploadBtn:', uploadBtn);
        console.log('loading:', loading);
        console.log('errorMsg:', errorMsg);
        console.log('resultSection:', resultSection);
        console.log('resultCards:', resultCards);
        console.log('downloadJson:', downloadJson);
        return;
    }

    console.log('✅ All elements found');

    let extractedData = null;

    // Upload button click handler
    uploadBtn.addEventListener('click', async function() {
        console.log('🔘 Upload button clicked');
        
        const file = fileInput.files[0];
        console.log('Selected file:', file);
        
        if (!file) {
            showError('Please select a file first!');
            return;
        }
        
        // Validate file type
        const validTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
        console.log('File type:', file.type);
        
        if (!validTypes.includes(file.type)) {
            showError('Please upload a valid PDF or image file (JPG, PNG)');
            return;
        }
        
        // Prepare form data
        const formData = new FormData();
        formData.append('file', file);
        console.log('FormData prepared');
        
        // Show loading state
        loading.classList.remove('hidden');
        errorMsg.classList.add('hidden');
        resultSection.classList.add('hidden');
        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Processing...';
        
        console.log('📤 Sending request to backend...');
        
        try {
            // Send request to backend
            const response = await fetch('http://localhost:5000/api/upload', {
                method: 'POST',
                body: formData
            });
            
            console.log('Response status:', response.status);
            
            const data = await response.json();
            console.log('Response data:', data);
            
            if (data.success) {
                extractedData = data.data;
                displayResults(data.data);
                errorMsg.classList.add('hidden');
                console.log('✅ Data extracted successfully');
            } else {
                showError(data.error || 'Failed to extract data');
            }
        } catch (error) {
            console.error('❌ Upload error:', error);
            showError('Connection error! Make sure the backend server is running on port 5000.');
        } finally {
            loading.classList.add('hidden');
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'Upload & Extract';
        }
    });

    // Display extracted results
    function displayResults(data) {
        console.log('📊 Displaying results:', data);
        
        const fields = [
            { key: 'name', label: 'Name', icon: '👤' },
            { key: 'gender', label: 'Gender', icon: '⚧' },
            { key: 'dob', label: 'Date of Birth', icon: '📅' },
            { key: 'aadhaar_number', label: 'Aadhaar Number', icon: '🔢' },
            { key: 'vid', label: 'VID', icon: '🆔' },
            { key: 'address', label: 'Address', icon: '📍' }
        ];
        
        resultCards.innerHTML = fields.map(field => {
            const value = data[field.key] || 'Not found';
            return `
                <div class="card">
                    <div class="card-icon">${field.icon}</div>
                    <div class="card-content">
                        <div class="card-label">${field.label}</div>
                        <div class="card-value">${value}</div>
                    </div>
                </div>
            `;
        }).join('');
        
        resultSection.classList.remove('hidden');
    }

    // Show error message
    function showError(message) {
        console.error('⚠️ Error:', message);
        errorMsg.textContent = '❌ ' + message;
        errorMsg.classList.remove('hidden');
    }

    // Download JSON button
    downloadJson.addEventListener('click', function() {
        console.log('💾 Download JSON clicked');
        
        if (!extractedData) {
            showError('No data to download');
            return;
        }
        
        const dataStr = JSON.stringify(extractedData, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = 'aadhaar_extracted_data.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        console.log('✅ JSON downloaded');
    });

    // File input change handler - show selected file name
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            const fileName = e.target.files[0].name;
            console.log('📁 Selected file:', fileName);
        }
    });

    console.log('✅ All event listeners attached');
});