import React, { useState, useEffect, useCallback } from 'react';
import {
  StyleSheet, Text, View, FlatList, TouchableOpacity,
  TextInput, ActivityIndicator, ScrollView, SafeAreaView,
  StatusBar, RefreshControl, Alert,
} from 'react-native';
import { StatusBar as ExpoStatusBar } from 'expo-status-bar';

// EAS sets EXPO_PUBLIC_API_URL per build profile (development/preview/production)
const API_BASE = (process.env.EXPO_PUBLIC_API_URL ?? 'http://10.0.2.2:8000') + '/api/v1';
// Local dev alternatives:
//   Android emulator:  http://10.0.2.2:8000/api/v1
//   iOS simulator:     http://localhost:8000/api/v1
//   Physical device:   http://YOUR_LOCAL_IP:8000/api/v1

const GREEN  = '#2e7d32';
const LIGHT  = '#e8f5e9';
const ORANGE = '#e65100';
const RED    = '#c62828';
const GREY   = '#757575';

// ── API helpers ───────────────────────────────────────────────────────────────

let _token = null;

async function api(path, opts = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(_token ? { Authorization: `Bearer ${_token}` } : {}),
      ...opts.headers,
    },
    ...opts,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : {};
  if (!res.ok) throw new Error(data?.detail ?? `HTTP ${res.status}`);
  return data;
}

// ── Status badge ──────────────────────────────────────────────────────────────

const STATUS_COLOR = { pending: ORANGE, approved: GREEN, rejected: RED };
const STATUS_LABEL = { pending: 'Pending', approved: 'Approved', rejected: 'Rejected' };

function StatusBadge({ status }) {
  return (
    <View style={[styles.badge, { backgroundColor: STATUS_COLOR[status] + '22' }]}>
      <Text style={[styles.badgeText, { color: STATUS_COLOR[status] }]}>
        {STATUS_LABEL[status] ?? status}
      </Text>
    </View>
  );
}

// ── Login screen ─────────────────────────────────────────────────────────────

function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);

  async function handleLogin() {
    if (!username.trim() || !password) { setError('Enter username and password'); return; }
    setLoading(true); setError(null);
    try {
      const data = await api('/users/login', {
        method: 'POST',
        body: JSON.stringify({ username: username.trim(), password }),
      });
      _token = data.access_token;
      onLogin(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.loginContainer}>
      <ExpoStatusBar style="light" />
      <View style={styles.loginCard}>
        <Text style={styles.loginEmoji}>🌾</Text>
        <Text style={styles.loginTitle}>AgriPermit</Text>
        <Text style={styles.loginSubtitle}>Agricultural Land Permit System</Text>

        {error && <Text style={styles.errorText}>{error}</Text>}

        <TextInput
          style={styles.input}
          placeholder="Username"
          autoCapitalize="none"
          value={username}
          onChangeText={setUsername}
        />
        <TextInput
          style={styles.input}
          placeholder="Password"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />
        <TouchableOpacity
          style={[styles.btnPrimary, loading && styles.btnDisabled]}
          onPress={handleLogin}
          disabled={loading}
        >
          {loading
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.btnPrimaryText}>Sign In</Text>}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

// ── Permit row ────────────────────────────────────────────────────────────────

function PermitRow({ permit, onPress }) {
  return (
    <TouchableOpacity style={styles.permitRow} onPress={() => onPress(permit)}>
      <View style={styles.permitRowTop}>
        <Text style={styles.permitNumber}>{permit.permit_number}</Text>
        <StatusBadge status={permit.status} />
      </View>
      <Text style={styles.permitApplicant}>{permit.applicant_name}</Text>
      <Text style={styles.permitMeta}>
        {permit.parcel_id}  ·  {new Date(permit.created_at).toLocaleDateString()}
        {permit.gis_blocked ? '  ⛔' : permit.gis_flagged ? '  ⚠' : ''}
      </Text>
    </TouchableOpacity>
  );
}

// ── Permit detail modal ───────────────────────────────────────────────────────

function PermitDetail({ permit: initial, user, onClose, onUpdated }) {
  const [permit, setPermit] = useState(initial);
  const [step, setStep]     = useState('view');   // 'view' | 'approve' | 'reject'
  const [approver, setApprover] = useState(user?.full_name ?? '');
  const [reason, setReason]   = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function submit(action) {
    if (!approver.trim()) { Alert.alert('Required', 'Enter approver name'); return; }
    if (action === 'reject' && !reason.trim()) { Alert.alert('Required', 'Enter rejection reason'); return; }
    setSubmitting(true);
    try {
      const updated = await api(`/permits/${permit.id}/approve`, {
        method: 'POST',
        body: JSON.stringify({
          action,
          approved_by: approver.trim(),
          rejection_reason: action === 'reject' ? reason.trim() : undefined,
        }),
      });
      setPermit(updated);
      setStep('view');
      onUpdated?.();
    } catch (err) {
      Alert.alert('Error', err.message);
    } finally {
      setSubmitting(false);
    }
  }

  const canAct = user?.role === 'admin' || user?.role === 'reviewer';

  return (
    <SafeAreaView style={styles.detailContainer}>
      <View style={styles.detailHeader}>
        <TouchableOpacity onPress={onClose} style={styles.backBtn}>
          <Text style={styles.backBtnText}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.detailTitle}>{permit.permit_number}</Text>
      </View>

      <ScrollView style={styles.detailBody} contentContainerStyle={{ paddingBottom: 40 }}>
        <View style={styles.detailCard}>
          <Row label="Applicant"  value={permit.applicant_name} />
          <Row label="Email"      value={permit.applicant_email} />
          <Row label="Parcel"     value={permit.parcel_id} />
          <Row label="Type"       value={permit.permit_type} />
          <Row label="Submitted"  value={new Date(permit.created_at).toLocaleString()} />
          {permit.description ? <Row label="Description" value={permit.description} /> : null}
        </View>

        <View style={[styles.detailCard, { marginTop: 12 }]}>
          <Text style={styles.detailSectionTitle}>Status</Text>
          <StatusBadge status={permit.status} />
          {permit.approved_by && <Row label="Handled by" value={permit.approved_by} />}
          {permit.rejection_reason && <Row label="Reason" value={permit.rejection_reason} />}
        </View>

        {(permit.gis_flagged || permit.gis_blocked) && (
          <View style={[styles.detailCard, styles.gisCard, { marginTop: 12 }]}>
            <Text style={styles.detailSectionTitle}>
              {permit.gis_blocked ? '⛔ GIS Blocked' : '⚠ GIS Warning'}
            </Text>
            {(permit.gis_violations ?? []).map((v, i) => (
              <Text key={i} style={[styles.violation, v.severity === 'block' ? styles.violationBlock : styles.violationWarn]}>
                {v.severity === 'block' ? '⛔' : '⚠'} {v.message}
              </Text>
            ))}
          </View>
        )}

        {canAct && permit.status === 'pending' && step === 'view' && (
          <View style={styles.actionCard}>
            <Text style={styles.detailSectionTitle}>Action</Text>
            <View style={styles.actionBtns}>
              <TouchableOpacity style={[styles.btnPrimary, { flex: 1, marginEnd: 8 }]} onPress={() => setStep('approve')}>
                <Text style={styles.btnPrimaryText}>Approve</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.btnReject, { flex: 1 }]} onPress={() => setStep('reject')}>
                <Text style={styles.btnPrimaryText}>Reject</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {canAct && permit.status === 'pending' && (step === 'approve' || step === 'reject') && (
          <View style={styles.actionCard}>
            <Text style={styles.detailSectionTitle}>
              {step === 'approve' ? 'Confirm Approval' : 'Confirm Rejection'}
            </Text>
            <Text style={styles.inputLabel}>Approved by *</Text>
            <TextInput style={styles.input} value={approver} onChangeText={setApprover} placeholder="Full name" />
            {step === 'reject' && (
              <>
                <Text style={styles.inputLabel}>Rejection reason *</Text>
                <TextInput
                  style={[styles.input, { height: 80, textAlignVertical: 'top' }]}
                  value={reason}
                  onChangeText={setReason}
                  placeholder="Specify reason"
                  multiline
                />
              </>
            )}
            <View style={styles.actionBtns}>
              <TouchableOpacity
                style={[step === 'approve' ? styles.btnPrimary : styles.btnReject, { flex: 1, marginEnd: 8 }, submitting && styles.btnDisabled]}
                onPress={() => submit(step)}
                disabled={submitting}
              >
                {submitting
                  ? <ActivityIndicator color="#fff" />
                  : <Text style={styles.btnPrimaryText}>{step === 'approve' ? 'Confirm' : 'Reject'}</Text>}
              </TouchableOpacity>
              <TouchableOpacity style={[styles.btnSecondary, { flex: 1 }]} onPress={() => setStep('view')} disabled={submitting}>
                <Text style={styles.btnSecondaryText}>Cancel</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function Row({ label, value }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

// ── Permits list screen ───────────────────────────────────────────────────────

function PermitsScreen({ user, onSignOut }) {
  const [permits, setPermits]   = useState([]);
  const [stats, setStats]       = useState(null);
  const [loading, setLoading]   = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError]       = useState(null);
  const [selected, setSelected] = useState(null);
  const [filterStatus, setFilter] = useState('');

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: 50 });
      if (filterStatus) params.set('status', filterStatus);
      const [data, s] = await Promise.all([
        api(`/permits?${params}`),
        api('/stats'),
      ]);
      setPermits(data.items);
      setStats(s);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filterStatus]);

  useEffect(() => { load(); }, [load]);

  const FILTERS = [
    { label: 'All',      value: '' },
    { label: 'Pending',  value: 'pending' },
    { label: 'Approved', value: 'approved' },
    { label: 'Rejected', value: 'rejected' },
  ];

  if (selected) {
    return (
      <PermitDetail
        permit={selected}
        user={user}
        onClose={() => setSelected(null)}
        onUpdated={() => load(true)}
      />
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ExpoStatusBar style="light" />

      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>AgriPermit</Text>
          <Text style={styles.headerSub}>{user.full_name} · {user.role}</Text>
        </View>
        <TouchableOpacity onPress={onSignOut} style={styles.signOutBtn}>
          <Text style={styles.signOutText}>Sign out</Text>
        </TouchableOpacity>
      </View>

      {/* Stats bar */}
      {stats && (
        <View style={styles.statsBar}>
          {[
            { label: 'Total',    value: stats.total,       color: GREEN },
            { label: 'Pending',  value: stats.pending,     color: ORANGE },
            { label: 'Approved', value: stats.approved,    color: GREEN },
            { label: 'Blocked',  value: stats.gis_blocked, color: RED },
          ].map(s => (
            <View key={s.label} style={styles.statTile}>
              <Text style={[styles.statValue, { color: s.color }]}>{s.value}</Text>
              <Text style={styles.statLabel}>{s.label}</Text>
            </View>
          ))}
        </View>
      )}

      {/* Filter pills */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterBar} contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}>
        {FILTERS.map(f => (
          <TouchableOpacity
            key={f.value}
            style={[styles.filterPill, filterStatus === f.value && styles.filterPillActive]}
            onPress={() => setFilter(f.value)}
          >
            <Text style={[styles.filterPillText, filterStatus === f.value && styles.filterPillTextActive]}>
              {f.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {error && <Text style={styles.errorText}>{error}</Text>}

      {loading && !refreshing
        ? <ActivityIndicator style={{ marginTop: 40 }} color={GREEN} size="large" />
        : (
          <FlatList
            data={permits}
            keyExtractor={p => p.id}
            renderItem={({ item }) => <PermitRow permit={item} onPress={setSelected} />}
            ListEmptyComponent={<Text style={styles.emptyText}>No permits found.</Text>}
            contentContainerStyle={{ padding: 16 }}
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={() => { setRefreshing(true); load(true); }}
                colors={[GREEN]}
              />
            }
          />
        )
      }
    </SafeAreaView>
  );
}

// ── Root ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [user, setUser] = useState(null);

  if (!user) return <LoginScreen onLogin={setUser} />;
  return <PermitsScreen user={user} onSignOut={() => { _token = null; setUser(null); }} />;
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  // Login
  loginContainer: { flex: 1, backgroundColor: '#f1f8e9', justifyContent: 'center', alignItems: 'center', padding: 24 },
  loginCard:      { backgroundColor: '#fff', borderRadius: 16, padding: 32, width: '100%', maxWidth: 380, alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.08, shadowRadius: 12, elevation: 4 },
  loginEmoji:     { fontSize: 48, marginBottom: 8 },
  loginTitle:     { fontSize: 28, fontWeight: '800', color: GREEN, marginBottom: 4 },
  loginSubtitle:  { fontSize: 13, color: GREY, marginBottom: 24, textAlign: 'center' },

  // Inputs
  input:      { width: '100%', borderWidth: 1, borderColor: '#ccc', borderRadius: 8, padding: 12, fontSize: 15, marginBottom: 12, backgroundColor: '#fafafa' },
  inputLabel: { fontSize: 13, fontWeight: '600', color: '#333', marginBottom: 4, marginTop: 4 },

  // Buttons
  btnPrimary:     { backgroundColor: GREEN, borderRadius: 8, padding: 14, alignItems: 'center', width: '100%' },
  btnPrimaryText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  btnReject:      { backgroundColor: RED,   borderRadius: 8, padding: 14, alignItems: 'center' },
  btnSecondary:   { backgroundColor: '#e8f5e9', borderRadius: 8, padding: 14, alignItems: 'center' },
  btnSecondaryText: { color: GREEN, fontWeight: '700', fontSize: 15 },
  btnDisabled:    { opacity: 0.55 },

  // Main layout
  container: { flex: 1, backgroundColor: '#f4f6f4' },
  header:    { backgroundColor: GREEN, padding: 16, paddingTop: StatusBar.currentHeight ?? 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerTitle: { color: '#fff', fontSize: 18, fontWeight: '800' },
  headerSub:   { color: 'rgba(255,255,255,.7)', fontSize: 12, marginTop: 2 },
  signOutBtn:  { backgroundColor: 'rgba(255,255,255,.15)', borderRadius: 6, paddingHorizontal: 12, paddingVertical: 6 },
  signOutText: { color: '#fff', fontSize: 13, fontWeight: '600' },

  // Stats
  statsBar:  { flexDirection: 'row', backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  statTile:  { flex: 1, alignItems: 'center', paddingVertical: 10 },
  statValue: { fontSize: 20, fontWeight: '800' },
  statLabel: { fontSize: 11, color: GREY, marginTop: 2 },

  // Filter pills
  filterBar:  { maxHeight: 52, paddingVertical: 10, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  filterPill: { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20, borderWidth: 1, borderColor: '#c8e6c9', backgroundColor: '#fff' },
  filterPillActive:     { backgroundColor: GREEN, borderColor: GREEN },
  filterPillText:       { color: GREY, fontSize: 13, fontWeight: '600' },
  filterPillTextActive: { color: '#fff' },

  // Permit list row
  permitRow:      { backgroundColor: '#fff', borderRadius: 10, padding: 14, marginBottom: 10, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 4, elevation: 2 },
  permitRowTop:   { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  permitNumber:   { fontFamily: 'monospace', fontSize: 13, color: '#555', fontWeight: '600' },
  permitApplicant:{ fontSize: 15, fontWeight: '700', color: '#1a1a1a', marginBottom: 2 },
  permitMeta:     { fontSize: 12, color: GREY },

  // Badge
  badge:     { paddingHorizontal: 10, paddingVertical: 3, borderRadius: 12 },
  badgeText: { fontSize: 12, fontWeight: '700' },

  // Detail
  detailContainer: { flex: 1, backgroundColor: '#f4f6f4' },
  detailHeader:    { backgroundColor: GREEN, flexDirection: 'row', alignItems: 'center', padding: 16, gap: 12 },
  detailTitle:     { color: '#fff', fontSize: 16, fontWeight: '800', fontFamily: 'monospace' },
  backBtn:         { paddingVertical: 4, paddingHorizontal: 8 },
  backBtnText:     { color: '#fff', fontSize: 14, fontWeight: '600' },
  detailBody:      { flex: 1, padding: 16 },
  detailCard:      { backgroundColor: '#fff', borderRadius: 10, padding: 16, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 4, elevation: 2 },
  detailSectionTitle: { fontSize: 13, fontWeight: '700', color: '#555', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 10 },
  row:       { flexDirection: 'row', paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: '#f5f5f5' },
  rowLabel:  { flex: 1, fontSize: 13, color: GREY, fontWeight: '600' },
  rowValue:  { flex: 2, fontSize: 13, color: '#1a1a1a' },
  actionCard: { backgroundColor: '#fff', borderRadius: 10, padding: 16, marginTop: 12, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 4, elevation: 2 },
  actionBtns: { flexDirection: 'row', marginTop: 12 },
  gisCard:    { borderWidth: 1, borderColor: '#ffe082', backgroundColor: '#fff8e1' },
  violation:      { fontSize: 13, marginBottom: 4, lineHeight: 18 },
  violationBlock: { color: RED },
  violationWarn:  { color: ORANGE },

  // Misc
  errorText: { color: RED, padding: 16, textAlign: 'center', fontSize: 13 },
  emptyText: { color: GREY, textAlign: 'center', marginTop: 40, fontSize: 15 },
});
