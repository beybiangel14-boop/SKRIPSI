import math
from datetime import datetime

class MinMaxScalerPure:
    """Implementasi MinMaxScaler dalam pure Python."""
    def __init__(self):
        self.min_val = None
        self.max_val = None

    def fit(self, data):
        # data adalah list of numbers
        if not data:
            self.min_val = 0.0
            self.max_val = 1.0
            return self
        self.min_val = min(data)
        self.max_val = max(data)
        # Cegah pembagian dengan nol jika min == max
        if self.min_val == self.max_val:
            self.max_val += 1e-6
        return self

    def transform(self, data):
        if self.min_val is None or self.max_val is None:
            raise ValueError("Scaler belum di-fit.")
        return [(x - self.min_val) / (self.max_val - self.min_val) for x in data]

    def fit_transform(self, data):
        return self.fit(data).transform(data)


class KMeansPure:
    """Implementasi K-Means Clustering dalam pure Python."""
    def __init__(self, n_clusters=3, max_iter=100):
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.centroids = []
        self.labels_ = []

    def fit(self, X):
        # 1. Validasi input X
        if not X or len(X) == 0:
            self.centroids = []
            self.labels_ = []
            return self

        n_samples = len(X)
        n_features = len(X[0])

        # Validasi k: k tidak boleh lebih besar dari n_samples dan minimal 1
        k = min(self.n_clusters, n_samples)
        if k < 1:
            k = 1
        self.n_clusters = k

        # 2. Inisialisasi Sentroid secara Deterministik sejumlah k sentroid
        # Urutkan indeks sampel berdasarkan total nilai fitur (R + F + M)
        sorted_indices = sorted(range(n_samples), key=lambda i: sum(X[i]))

        self.centroids = []
        for i in range(k):
            if k == 1:
                idx = sorted_indices[0]
            else:
                idx = sorted_indices[int(i * (n_samples - 1) / (k - 1))]
            self.centroids.append(list(X[idx]))

        # Validasi struktur sentroid
        assert len(self.centroids) == self.n_clusters, f"Jumlah centroid ({len(self.centroids)}) tidak sesuai dengan k ({self.n_clusters})"
        for c in self.centroids:
            assert len(c) == n_features, f"Jumlah fitur centroid ({len(c)}) tidak sesuai dengan n_features ({n_features})"

        for _ in range(self.max_iter):
            # A. Tahap Asosiasi (Assign Clusters)
            labels = []
            for sample in X:
                distances = [self._euclidean_distance(sample, centroid) for centroid in self.centroids]
                closest_centroid = distances.index(min(distances))
                labels.append(closest_centroid)

            # B. Tahap Pembaruan Sentroid (Update Centroids)
            new_centroids = [[0.0] * n_features for _ in range(self.n_clusters)]
            counts = [0] * self.n_clusters
            
            for i, label in enumerate(labels):
                for j in range(n_features):
                    new_centroids[label][j] += X[i][j]
                counts[label] += 1

            for label in range(self.n_clusters):
                if counts[label] > 0:
                    new_centroids[label] = [val / counts[label] for val in new_centroids[label]]
                else:
                    new_centroids[label] = list(self.centroids[label])

            # C. Cek Konvergensi
            if self._has_converged(self.centroids, new_centroids):
                self.centroids = new_centroids
                self.labels_ = labels
                break
                
            self.centroids = new_centroids
            self.labels_ = labels

        return self

    def _euclidean_distance(self, p1, p2):
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(p1, p2)))

    def _has_converged(self, old_c, new_c, tol=1e-6):
        for o, n in zip(old_c, new_c):
            if self._euclidean_distance(o, n) > tol:
                return False
        return True


def calculate_percentile(data, percentile):
    """Menghitung nilai persentil dari suatu list angka."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    return sorted_data[int(f)] * (c - k) + sorted_data[int(c)] * (k - f)


def calculate_rfm(pelanggan_list, transaksi_list, tanggal_analisis=None):
    """
    Menghitung nilai Recency, Frequency, dan Monetary dari data transaksi pelanggan,
    serta menghitung skor RFM menggunakan metode Tertile.
    """
    if not tanggal_analisis:
        tanggal_analisis = datetime.now().date()

    # 1. Inisialisasi RFM dict untuk setiap pelanggan
    rfm_data = {}
    for p in pelanggan_list:
        rfm_data[p['id']] = {
            'id': p['id'],
            'nama_pelanggan': p['nama_pelanggan'],
            'last_transaction_date': None,
            'recency': 9999, # Default jika tidak ada transaksi
            'frequency': 0,
            'monetary': 0.0
        }

    # 2. Hitung Recency, Frequency, Monetary dari data transaksi
    for t in transaksi_list:
        pid = t['pelanggan_id']
        if pid not in rfm_data:
            continue
        
        # Format tanggal transaksi (pastikan date object)
        t_date = t['tanggal_transaksi']
        if isinstance(t_date, datetime):
            t_date = t_date.date()
        elif isinstance(t_date, str):
            t_date = datetime.strptime(t_date, '%Y-%m-%d').date()

        # Update tanggal transaksi terakhir
        if rfm_data[pid]['last_transaction_date'] is None or t_date > rfm_data[pid]['last_transaction_date']:
            rfm_data[pid]['last_transaction_date'] = t_date

        rfm_data[pid]['frequency'] += 1
        rfm_data[pid]['monetary'] += float(t['total_transaksi'])

    # Hitung Recency dalam hari
    for pid, data in rfm_data.items():
        if data['last_transaction_date'] is not None:
            data['recency'] = (tanggal_analisis - data['last_transaction_date']).days
            # Cegah nilai negatif jika tanggal transaksi di masa depan
            if data['recency'] < 0:
                data['recency'] = 0

    rfm_list = list(rfm_data.values())
    
    # Jika tidak ada data pelanggan atau transaksi
    if not rfm_list:
        return []

    # 3. Hitung Skor RFM menggunakan Tertiles (Skala 1 - 3)
    recencies = [x['recency'] for x in rfm_list if x['frequency'] > 0]
    frequencies = [x['frequency'] for x in rfm_list if x['frequency'] > 0]
    monetaries = [x['monetary'] for x in rfm_list if x['frequency'] > 0]

    # Thresholds untuk tertile (33.33% dan 66.67%)
    r_33 = calculate_percentile(recencies, 33.33) if recencies else 0
    r_66 = calculate_percentile(recencies, 66.67) if recencies else 0
    f_33 = calculate_percentile(frequencies, 33.33) if frequencies else 0
    f_66 = calculate_percentile(frequencies, 66.67) if frequencies else 0
    m_33 = calculate_percentile(monetaries, 33.33) if monetaries else 0
    m_66 = calculate_percentile(monetaries, 66.67) if monetaries else 0

    for item in rfm_list:
        if item['frequency'] == 0:
            item['r_score'] = 1
            item['f_score'] = 1
            item['m_score'] = 1
            item['score_rfm'] = 3.0
            continue

        # Recency: Lebih kecil hari = lebih baik (skor 3)
        if item['recency'] <= r_33:
            item['r_score'] = 3
        elif item['recency'] <= r_66:
            item['r_score'] = 2
        else:
            item['r_score'] = 1

        # Frequency: Lebih sering = lebih baik (skor 3)
        if item['frequency'] <= f_33:
            item['f_score'] = 1
        elif item['frequency'] <= f_66:
            item['f_score'] = 2
        else:
            item['f_score'] = 3

        # Monetary: Lebih besar nominal = lebih baik (skor 3)
        if item['monetary'] <= m_33:
            item['m_score'] = 1
        elif item['monetary'] <= m_66:
            item['m_score'] = 2
        else:
            item['m_score'] = 3

        # Skor RFM Rata-rata
        item['score_rfm'] = round((item['r_score'] + item['f_score'] + item['m_score']) / 3, 2)

    return rfm_list


def run_kmeans_only(rfm_list):
    """
    Menjalankan K-Means Clustering K=3 berdasarkan data RFM yang diberikan.
    """
    # Jika tidak ada data pelanggan atau transaksi
    if not rfm_list:
        return []

    # 4. Normalisasi MinMax untuk K-Means
    # Ambil data untuk clustering (hanya pelanggan yang memiliki transaksi)
    clustered_items = [x for x in rfm_list if x['frequency'] > 0]
    
    if not clustered_items:
        # Jika tidak ada pelanggan dengan transaksi
        for item in rfm_list:
            item['cluster'] = 2 # Default C3 Non Aktif
            item['segmentasi'] = 'Pelanggan Non Aktif'
        return rfm_list

    r_vals = [float(x['recency']) for x in clustered_items]
    f_vals = [float(x['frequency']) for x in clustered_items]
    m_vals = [float(x['monetary']) for x in clustered_items]

    scaler_r = MinMaxScalerPure().fit(r_vals)
    scaler_f = MinMaxScalerPure().fit(f_vals)
    scaler_m = MinMaxScalerPure().fit(m_vals)

    r_norm = scaler_r.transform(r_vals)
    f_norm = scaler_f.transform(f_vals)
    m_norm = scaler_m.transform(m_vals)

    X = [[rn, fn, mn] for rn, fn, mn in zip(r_norm, f_norm, m_norm)]

    # 5. Jalankan K-Means Clustering (K=3)
    kmeans = KMeansPure(n_clusters=3).fit(X)
    labels = kmeans.labels_
    centroids = kmeans.centroids

    # 6. Pemetaan Cluster ke C1 (Loyal), C2 (Aktif), C3 (Non-Aktif) secara matematis
    # Formula kualitas sentroid: Quality = F_centroid + M_centroid - R_centroid
    centroid_qualities = []
    for i, c in enumerate(centroids):
        # c = [r_centroid, f_centroid, m_centroid]
        quality = c[1] + c[2] - c[0]
        centroid_qualities.append((i, quality))

    # Urutkan berdasarkan kualitas dari yang tertinggi ke terendah
    # Urutan: Index 0 tertinggi (Loyal), Index 1 sedang (Aktif), Index 2 terendah (Non-Aktif)
    sorted_by_quality = sorted(centroid_qualities, key=lambda x: x[1], reverse=True)
    
    cluster_mapping = {}
    cluster_mapping[sorted_by_quality[0][0]] = (0, 'Pelanggan Loyal')      # Kualitas tertinggi -> C1
    cluster_mapping[sorted_by_quality[1][0]] = (1, 'Pelanggan Aktif')      # Kualitas sedang -> C2
    cluster_mapping[sorted_by_quality[2][0]] = (2, 'Pelanggan Non Aktif')  # Kualitas terendah -> C3

    # Masukkan hasil cluster ke dalam list utama
    cluster_idx = 0
    for item in rfm_list:
        if item['frequency'] == 0:
            item['cluster'] = 2 # C3 Non Aktif
            item['segmentasi'] = 'Pelanggan Non Aktif'
        else:
            original_label = labels[cluster_idx]
            db_label, label_name = cluster_mapping[original_label]
            item['cluster'] = db_label
            item['segmentasi'] = label_name
            cluster_idx += 1

    return rfm_list


def process_rfm_and_kmeans(pelanggan_list, transaksi_list, tanggal_analisis=None):
    """
    Menghitung RFM, melakukan normalisasi, menjalankan K-Means (K=3), 
    serta menghitung skor RFM menggunakan metode Tertile.
    
    pelanggan_list: list dari dict {'id': id, 'nama': nama}
    transaksi_list: list dari dict {'pelanggan_id': pid, 'tanggal': date_obj, 'total': float}
    """
    rfm_list = calculate_rfm(pelanggan_list, transaksi_list, tanggal_analisis)
    return run_kmeans_only(rfm_list)


def calculate_elbow_method(rfm_list, max_k=6):
    """
    Menghitung inertia (Sum of Squared Errors / SSE) untuk nilai K=2..max_k
    menggunakan data RFM yang sudah dinormalisasi.
    """
    clustered_items = [x for x in rfm_list if x.get('frequency', 0) > 0]
    if not clustered_items:
        return {
            'k_values': list(range(2, max_k + 1)),
            'sse_values': [0.0] * (max_k - 1),
            'optimal_k': 3
        }

    r_vals = [float(x['recency']) for x in clustered_items]
    f_vals = [float(x['frequency']) for x in clustered_items]
    m_vals = [float(x['monetary']) for x in clustered_items]

    scaler_r = MinMaxScalerPure().fit(r_vals)
    scaler_f = MinMaxScalerPure().fit(f_vals)
    scaler_m = MinMaxScalerPure().fit(m_vals)

    X = [
        [r, f, m]
        for r, f, m in zip(
            scaler_r.transform(r_vals),
            scaler_f.transform(f_vals),
            scaler_m.transform(m_vals)
        )
    ]

    n_samples = len(X)
    max_k_possible = min(max_k, n_samples)
    if max_k_possible < 2:
        return {
            'k_values': [2, 3],
            'sse_values': [0.0, 0.0],
            'optimal_k': 3
        }

    k_values = list(range(2, max_k_possible + 1))
    sse_values = []

    for k in k_values:
        kmeans = KMeansPure(n_clusters=k).fit(X)
        centroids = kmeans.centroids
        labels = kmeans.labels_

        sse = 0.0
        for i, sample in enumerate(X):
            c_idx = labels[i]
            c = centroids[c_idx]
            dist_sq = sum((s - cent) ** 2 for s, cent in zip(sample, c))
            sse += dist_sq

        sse_values.append(round(sse, 4))

    # Mendeteksi titik siku (Elbow point)
    optimal_k = 3
    if len(sse_values) >= 3:
        diffs = [sse_values[i] - sse_values[i+1] for i in range(len(sse_values)-1)]
        diff_of_diffs = [diffs[i] - diffs[i+1] for i in range(len(diffs)-1)]
        if diff_of_diffs:
            max_idx = diff_of_diffs.index(max(diff_of_diffs))
            optimal_k = k_values[max_idx + 1]

    return {
        'k_values': k_values,
        'sse_values': sse_values,
        'optimal_k': optimal_k
    }


def calculate_silhouette_score(X, labels):
    """
    Menghitung skor Silhouette Coefficient rata-rata untuk dataset X dan label cluster.
    """
    n_samples = len(X)
    if n_samples <= 1:
        return 0.0

    unique_labels = list(set(labels))
    if len(unique_labels) <= 1:
        return 0.0

    scores = []
    for i in range(n_samples):
        same_cluster = [X[j] for j in range(n_samples) if labels[j] == labels[i] and j != i]
        if not same_cluster:
            a_i = 0.0
        else:
            a_i = sum(math.sqrt(sum((x - y) ** 2 for x, y in zip(X[i], sample))) for sample in same_cluster) / len(same_cluster)

        b_i = float('inf')
        for label in unique_labels:
            if label == labels[i]:
                continue
            other_cluster = [X[j] for j in range(n_samples) if labels[j] == label]
            if other_cluster:
                avg_dist = sum(math.sqrt(sum((x - y) ** 2 for x, y in zip(X[i], sample))) for sample in other_cluster) / len(other_cluster)
                if avg_dist < b_i:
                    b_i = avg_dist

        if b_i == float('inf'):
            b_i = 0.0

        max_ab = max(a_i, b_i)
        if max_ab == 0:
            scores.append(0.0)
        else:
            scores.append((b_i - a_i) / max_ab)

    return round(sum(scores) / len(scores), 4)

