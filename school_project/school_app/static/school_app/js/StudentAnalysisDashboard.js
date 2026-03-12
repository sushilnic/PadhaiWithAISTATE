// static/school_app/js/StudentAnalysisDashboard.js

document.addEventListener('DOMContentLoaded', function() {
  const studentSelect = document.getElementById('studentSelect');
  const analysisContent = document.getElementById('analysisContent');

  // Fetch students when page loads
  fetchStudents();

  // Add change event listener to the select element
  studentSelect.addEventListener('change', function(e) {
      const selectedId = e.target.value;
      if (selectedId) {
          fetchStudentData(selectedId);
      } else {
          // Clear the analysis content if no student is selected
          analysisContent.innerHTML = '';
      }
  });

  async function fetchStudents() {
      try {
          const response = await fetch('/api/students/', {
              headers: {
                  'X-Requested-With': 'XMLHttpRequest'
              }
          });

          if (!response.ok) throw new Error('Failed to fetch students');

          const data = await response.json();
          if (data.students && Array.isArray(data.students)) {
              populateStudentSelect(data.students);
          }
      } catch (error) {
          console.error('Error:', error);
          showError('Failed to load students. Please refresh the page.');
      }
  }

  function populateStudentSelect(students) {
      studentSelect.innerHTML = '<option value="">Choose a student...</option>';
      students.sort((a, b) => a.name.localeCompare(b.name))
          .forEach(student => {
              const option = document.createElement('option');
              option.value = student.id;
              option.textContent = `${student.name} (Roll No: ${student.roll_number})`;
              studentSelect.appendChild(option);
          });
  }

  async function fetchStudentData(studentId) {
      try {
          const response = await fetch(`/api/student-analysis/${studentId}/`, {
              headers: {
                  'X-Requested-With': 'XMLHttpRequest'
              }
          });

          if (!response.ok) throw new Error('Failed to fetch student data');

          const data = await response.json();
          displayStudentAnalysis(data);
      } catch (error) {
          console.error('Error:', error);
          showError('Failed to load student analysis. Please try again.');
      }
  }

  function displayStudentAnalysis(data) {
      // Create the HTML content for student analysis with blue theme and chart containers
      const html = `
          <div class="card">
              <div class="card-header">
                  <h3>📋 Student Information</h3>
              </div>
              <div class="card-body">
                  <div class="row">
                      <div class="col-md-4 mb-3">
                          <div class="stat-label">Name</div>
                          <div class="stat-value">${data.name}</div>
                      </div>
                      <div class="col-md-4 mb-3">
                          <div class="stat-label">Roll Number</div>
                          <div class="stat-value">${data.roll_number}</div>
                      </div>
                      <div class="col-md-4 mb-3">
                          <div class="stat-label">Class</div>
                          <div class="stat-value">${data.class_name}</div>
                      </div>
                  </div>
              </div>
          </div>

          <div class="card">
              <div class="card-header">
                  <h3>📈 Performance Statistics</h3>
              </div>
              <div class="card-body">
                  <div class="row text-center">
                      <div class="col-md-3 col-6 mb-3">
                          <div class="stat-value">${data.statistics.average_marks}</div>
                          <div class="stat-label">Average Marks</div>
                      </div>
                      <div class="col-md-3 col-6 mb-3">
                          <div class="stat-value" style="color: #10b981;">${data.statistics.highest_mark}</div>
                          <div class="stat-label">Highest Mark</div>
                      </div>
                      <div class="col-md-3 col-6 mb-3">
                          <div class="stat-value" style="color: #ef4444;">${data.statistics.lowest_mark}</div>
                          <div class="stat-label">Lowest Mark</div>
                      </div>
                      <div class="col-md-3 col-6 mb-3">
                          <div class="stat-value">${data.statistics.total_tests}</div>
                          <div class="stat-label">Total Tests</div>
                      </div>
                  </div>
                  <div class="row mt-4">
                      <div class="col-12 mb-4">
                          <h5 style="color:#1e3c72;">Marks Trend</h5>
                          <canvas id="marksTrendChart" height="80"></canvas>
                      </div>
                      <div class="col-12">
                          <h5 style="color:#1e3c72;">Subject-wise Performance</h5>
                          <canvas id="subjectPerformanceChart" height="80"></canvas>
                      </div>
                  </div>
              </div>
          </div>

          <div class="card">
              <div class="card-header">
                  <h3>📝 Test Performance Details</h3>
              </div>
              <div class="card-body" style="padding: 0;">
                  <div class="table-responsive">
                      <table class="table table-striped">
                          <thead>
                              <tr>
                                  <th>Test Name</th>
                                  <th>Subject</th>
                                  <th>Date</th>
                                  <th>Marks</th>
                                  <th>Class Average</th>
                              </tr>
                          </thead>
                          <tbody>
                              ${data.test_performance.map(test => `
                                  <tr>
                                      <td>${test.test_name}</td>
                                      <td>${test.subject}</td>
                                      <td>${test.date || 'N/A'}</td>
                                      <td><strong>${test.marks}</strong></td>
                                      <td>${test.class_average || 'N/A'}</td>
                                  </tr>
                              `).join('')}
                          </tbody>
                      </table>
                  </div>
              </div>
          </div>
      `;

      // Update the analysis content
      analysisContent.innerHTML = html;

      // Render charts if data is available
      if (data.test_performance && data.test_performance.length > 0) {
          // Marks Trend Chart
          const marksTrendCtx = document.getElementById('marksTrendChart').getContext('2d');
          const marksTrendLabels = data.test_performance.map(t => t.test_name);
          const marksTrendData = data.test_performance.map(t => t.marks);
          new Chart(marksTrendCtx, {
              type: 'line',
              data: {
                  labels: marksTrendLabels,
                  datasets: [{
                      label: 'Marks',
                      data: marksTrendData,
                      borderColor: '#1e3c72',
                      backgroundColor: 'rgba(30,60,114,0.08)',
                      fill: true,
                      tension: 0.3,
                      pointBackgroundColor: '#38bdf8',
                      pointRadius: 5
                  }]
              },
              options: {
                  plugins: { legend: { display: false } },
                  scales: {
                      y: { beginAtZero: true, grid: { color: '#e2e8f0' } },
                      x: { grid: { color: '#e2e8f0' } }
                  }
              }
          });

          // Subject-wise Performance Chart
          const subjectMap = {};
          data.test_performance.forEach(t => {
              if (!subjectMap[t.subject]) subjectMap[t.subject] = [];
              subjectMap[t.subject].push(t.marks);
          });
          const subjectLabels = Object.keys(subjectMap);
          const subjectAverages = subjectLabels.map(sub => {
              const arr = subjectMap[sub];
              return arr.reduce((a, b) => a + b, 0) / arr.length;
          });
          const subjectColors = ['#1e3c72', '#2a5298', '#38bdf8', '#10b981', '#f59e42', '#ef4444'];
          const subjectPerformanceCtx = document.getElementById('subjectPerformanceChart').getContext('2d');
          new Chart(subjectPerformanceCtx, {
              type: 'bar',
              data: {
                  labels: subjectLabels,
                  datasets: [{
                      label: 'Average Marks',
                      data: subjectAverages,
                      backgroundColor: subjectColors.slice(0, subjectLabels.length),
                      borderRadius: 8
                  }]
              },
              options: {
                  plugins: { legend: { display: false } },
                  scales: {
                      y: { beginAtZero: true, grid: { color: '#e2e8f0' } },
                      x: { grid: { color: '#e2e8f0' } }
                  }
              }
          });
      }
  }

  function showError(message) {
      analysisContent.innerHTML = `
          <div class="alert alert-danger" role="alert">
              ${message}
          </div>
      `;
  }
});