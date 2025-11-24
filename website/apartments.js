// Load and display apartments from JSON
async function loadApartments() {
    try {
        const response = await fetch('apartments.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        displayApartments(data.apartments);
        updateStats(data);
    } catch (error) {
        console.error('Error loading apartments:', error);
        document.getElementById('apartments-container').innerHTML = 
            '<div class="col-12 text-center"><p class="text-danger">Error loading apartments. Please try again later.</p></div>';
    }
}

function displayApartments(apartments) {
    const container = document.getElementById('apartments-container');
    if (!container) return;
    
    if (!apartments || apartments.length === 0) {
        container.innerHTML = '<div class="col-12 text-center"><p>No apartments found.</p></div>';
        return;
    }
    
    container.innerHTML = apartments.map(apt => {
        // Handle null values safely
        const price = apt.price ? `$${apt.price.toLocaleString()}/mo` : 'Price not available';
        const sqft = apt.sqft ? `${apt.sqft} sqft` : 'Size not available';
        const distance = apt.distance_to_work !== null && apt.distance_to_work !== undefined ? `${apt.distance_to_work.toFixed(1)} km` : 'N/A';
        const commute = apt.commute_time !== null && apt.commute_time !== undefined ? `${apt.commute_time.toFixed(0)} min` : 'N/A';
        const imageUrl = (apt.images && apt.images.length > 0 && apt.images[0]) ? apt.images[0] : 'img/property-1.jpg';
        const bedrooms = apt.bedrooms !== null && apt.bedrooms !== undefined ? apt.bedrooms : 'N/A';
        const bathrooms = apt.bathrooms !== null && apt.bathrooms !== undefined ? apt.bathrooms : 'N/A';
        
        return `
        <div class="col-lg-4 col-md-6 wow fadeInUp" data-wow-delay="0.1s">
            <div class="property-item rounded overflow-hidden">
                <div class="position-relative overflow-hidden">
                    <a href="${apt.url || '#'}" target="_blank">
                        <img class="img-fluid" src="${imageUrl}" alt="${apt.title || 'Apartment'}" onerror="this.src='img/property-1.jpg'">
                    </a>
                    <div class="bg-primary rounded text-white position-absolute start-0 top-0 m-4 py-1 px-3">
                        ${apt.source || 'Unknown'}
                    </div>
                    <div class="bg-white rounded-top text-primary position-absolute start-0 bottom-0 mx-4 pt-1 px-3">
                        ${bedrooms} Bed | ${bathrooms} Bath
                    </div>
                </div>
                <div class="p-4 pb-0">
                    <h5 class="text-primary mb-3">${price}</h5>
                    <a class="d-block h5 mb-2" href="${apt.url || '#'}" target="_blank">${apt.title || 'Apartment'}</a>
                    <p><i class="fa fa-map-marker-alt text-primary me-2"></i>${apt.address || 'Address not available'}</p>
                </div>
                <div class="d-flex border-top p-4">
                    <small class="flex-fill text-center border-end py-2">
                        <i class="fa fa-ruler-combined text-primary me-2"></i>${sqft}
                    </small>
                    <small class="flex-fill text-center border-end py-2">
                        <i class="fa fa-road text-primary me-2"></i>${distance}
                    </small>
                    <small class="flex-fill text-center py-2">
                        <i class="fa fa-clock text-primary me-2"></i>${commute}
                    </small>
                </div>
                <div class="p-4 pt-0">
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="badge ${getMatchBadgeClass(apt.match_score || 0)} fs-6">
                            Match: ${apt.match_score || 0}%
                        </span>
                        ${apt.pet_friendly ? '<span class="badge bg-info">Pet Friendly</span>' : ''}
                    </div>
                    ${apt.amenities && apt.amenities.length > 0 ? `
                        <div class="mt-2">
                            <small class="text-muted">
                                <i class="fa fa-check-circle text-primary me-1"></i>
                                ${apt.amenities.slice(0, 3).join(', ')}
                            </small>
                        </div>
                    ` : ''}
                </div>
            </div>
        </div>
    `;
    }).join('');
}

function getMatchBadgeClass(score) {
    if (score >= 80) return 'bg-success';
    if (score >= 60) return 'bg-warning';
    return 'bg-secondary';
}

function updateStats(data) {
    const totalEl = document.getElementById('total-apartments');
    const updatedEl = document.getElementById('last-updated');
    
    if (totalEl) {
        totalEl.textContent = data.total_count || 0;
    }
    
    if (updatedEl) {
        if (data.last_updated) {
            const date = new Date(data.last_updated);
            updatedEl.textContent = date.toLocaleString();
        } else {
            updatedEl.textContent = 'Never';
        }
    }
}

// Load apartments when page loads
document.addEventListener('DOMContentLoaded', loadApartments);