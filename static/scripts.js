async function update_graph() {
    const loading  = document.getElementById('loading');
    const message  = document.getElementById('message');
    const sensor   = document.getElementById('sensor').value;
    let start_date = document.getElementById('start_date').value;
    let end_date   = document.getElementById('end_date').value;

    // dates validation
    if (!start_date && !end_date) {
        message.textContent = 'Specify date!';
        message.classList.add('visibile');
        return;
    }

    start_date = new Date(start_date);
    end_date = new Date(end_date);

    if (start_date > end_date) {
        message.textContent = 'Start date must be before end date!';
        message.classList.add('visibile');
        return;
    }

    message.classList.remove('visibile');
    loading.classList.add('visibile');

    try {
        const response = await fetch(`/api/graph_data?sensor=${sensor}&start_date=${start_date.toISOString().split('T')[0]}&end_date=${end_date.toISOString().split('T')[0]}`);

        if (!response.ok) {
            throw new Error((await response.json()).error ?? 'Error while loading data!');
        }

        const data = await response.json();

        if (data.error) {
            message.textContent = data.error;
            message.classList.add('visibile');
            loading.classList.remove('visibile');
            return;
        }

        makePlot(data, `Sensor data from <b>${start_date.toLocaleDateString()}</b> to <b>${end_date.toLocaleDateString()}</b>`);
    } catch (error) {
        message.textContent = 'Error: ' + error.message;
        message.classList.add('visibile');
    } finally {
        loading.classList.remove('visibile');
    }
}

// reset_graph i filtri e mostra tutti i data
function reset_graph() {
    document.getElementById('start_date').value = '';
    document.getElementById('end_date').value = '';
    document.getElementById('message').classList.remove('visibile');

    fetch('/api/graph_data')
        .then(response => response.json())
        .then((data) => { makePlot(data, 'All sensor data'); });
}

function makePlot(data, title) {
    // create graph with multiple independent axes
    Plotly.newPlot('graph', [{
        x: data.date,
        y: data.temp,
        name: 'Temperature (°C)',
        type: 'scatter',
        mode: 'lines',
        line: { color: '#e74c3c', width: 2 },
        yaxis: 'y1'
    }, {
        x: data.date,
        y: data.rh,
        name: 'Relative humidity (%)',
        type: 'scatter',
        mode: 'lines',
        line: {
            shape: 'spline',
            color: '#3498db',
            width: 2
        },
        yaxis: 'y2'
    }], {
        title: title,
        xaxis: { title: 'Date and time' },
        yaxis: {
            title: 'Temperature (°C)',
            titlefont: { color: '#e74c3c' },
            tickfont: { color: '#e74c3c' }
        },
        yaxis2: {
            title: 'Relative humidity (%)',
            titlefont: { color: '#3498db' },
            tickfont: { color: '#3498db' },
            overlaying: 'y',
            side: 'right',
            range: [0, 100]
        },
        hovermode: 'x unified',
        margin: { r: 80 }
    }, { responsive: true });
}


window.addEventListener('load', () => {
    // initialize dates: last avaiable within 1 month max timeframe

    const last_date    = new Date(document.getElementById('date_max').value);
    let   first_date   = new Date(document.getElementById('date_min').value);
    const month_before = new Date(last_date.getFullYear(), last_date.getMonth() - 1, last_date.getDate());

    first_date = month_before > first_date ? month_before : first_date;

    document.getElementById('end_date').value   = last_date.toISOString().split('T')[0];
    document.getElementById('start_date').value = first_date.toISOString().split('T')[0];

    update_graph();
});