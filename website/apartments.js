// Load and display apartments from JSON
async function loadApartments() {
    try {
        const response = await fetch('apartments.jon');
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
    
    container.innerHTML = apartments.map(apt => `
        <div class="col-lg-4 col-md-6 wow fadeInUp" data-wow-delay="0.1s">
            <div class="property-item rounded overflow-hidden">
                <div class="position-relative overflow-hidden">
                    <a href="${apt.url}" target="_blank">
                        <img class="img-fluid" src="${apt.images[0]}" alt="${apt.title}">
                    </a>
                    <div class="bg-primary rounded text-white position-absolute start-0 top-0 m-4 py-1 px-3">
                        ${apt.source}
                    </div>
                    <div class="bg-white rounded-top text-primary position-absolute start-0 bottom-0 mx-4 pt-1 px-3">
                        ${apt.bedrooms} Bed | ${apt.bathrooms} Bath
                    </div>
                </div>
                <div class="p-4 pb-0">
                    <h5 class="text-primary mb-3">$${apt.price.toLocaleString()}/mo</h5>
                    <a class="d-block h5 mb-2" href="${apt.url}" target="_blank">${apt.title}</a>
                    <p><i class="fa fa-map-marker-alt text-primary me-2"></i>${apt.address}</p>
                </div>
                <div class="d-flex border-top p-4">
                    <small class="flex-fill text-center border-end py-2">
                        <i class="fa fa-ruler-combined text-primary me-2"></i>${apt.sqft} sqft
                    </small>
                    <small class="flex-fill text-center border-end py-2">
                        <i class="fa fa-road text-primary me-2"></i>${apt.distance_to_work} km
                    </small>
                    <small class="flex-fill text-center py-2">
                        <i class="fa fa-clock text-primary me-2"></i>${apt.commute_time} min
                    </small>
                </div>
                <div class="p-4 pt-0">
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="badge ${getMatchBadgeClass(apt.match_score)} fs-6">
                            Match: ${apt.match_score}%
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
    `).join('');
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
        totalEl.textContent = data.total_count;
    }
    
    if (updatedEl) {
        const date = new Date(data.last_updated);
        updatedEl.textContent = date.toLocaleString();
    }
}

// Load apartments when page loads
document.addEventListener('DOMContentLoaded', loadApartments);