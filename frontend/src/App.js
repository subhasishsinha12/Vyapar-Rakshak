import React from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";

import { AuthProvider, useAuth } from "./lib/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import VendorLayout from "./components/VendorLayout";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import VerifyPayment from "./pages/VerifyPayment";
import PaymentDetail from "./pages/PaymentDetail";
import InvoiceScanner from "./pages/InvoiceScanner";
import Vendors from "./pages/Vendors";
import VendorDetail from "./pages/VendorDetail";
import Beneficiaries from "./pages/Beneficiaries";
import Approvals from "./pages/Approvals";
import FraudAlerts from "./pages/FraudAlerts";
import IncidentRoom from "./pages/IncidentRoom";
import IncidentDetail from "./pages/IncidentDetail";
import Reports from "./pages/Reports";
import AuditTrail from "./pages/AuditTrail";
import Settings from "./pages/Settings";
import Integrations from "./pages/Integrations";
import CommDetector from "./pages/CommDetector";
import VoiceVerification from "./pages/VoiceVerification";

import VendorHome from "./pages/vendor/VendorHome";
import VendorKyc from "./pages/vendor/VendorKyc";
import VendorPayments from "./pages/vendor/VendorPayments";
import VendorBankChange from "./pages/vendor/VendorBankChange";

function RoleRoot() {
  const { user, loading } = useAuth();
  if (loading || user === null) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-muted-foreground">Loading VyaparRakshak…</div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "vendor") return <Navigate to="/vendor" replace />;
  return <Layout><Dashboard /></Layout>;
}

function Shell({ children }) {
  return (
    <ProtectedRoute>
      <Layout>{children}</Layout>
    </ProtectedRoute>
  );
}

function VendorShell() {
  return (
    <ProtectedRoute>
      <VendorLayout />
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-right" richColors theme="dark" />
        <Routes>
          <Route path="/login" element={<Login />} />

          {/* Vendor portal */}
          <Route path="/vendor" element={<VendorShell />}>
            <Route index element={<VendorHome />} />
            <Route path="kyc" element={<VendorKyc />} />
            <Route path="payments" element={<VendorPayments />} />
            <Route path="bank-change" element={<VendorBankChange />} />
          </Route>

          {/* Buyer app */}
          <Route path="/" element={<RoleRoot />} />
          <Route path="/verify" element={<Shell><VerifyPayment /></Shell>} />
          <Route path="/verify/:id" element={<Shell><PaymentDetail /></Shell>} />
          <Route path="/scanner" element={<Shell><InvoiceScanner /></Shell>} />
          <Route path="/vendors" element={<Shell><Vendors /></Shell>} />
          <Route path="/vendors/:id" element={<Shell><VendorDetail /></Shell>} />
          <Route path="/beneficiaries" element={<Shell><Beneficiaries /></Shell>} />
          <Route path="/approvals" element={<Shell><Approvals /></Shell>} />
          <Route path="/alerts" element={<Shell><FraudAlerts /></Shell>} />
          <Route path="/incidents" element={<Shell><IncidentRoom /></Shell>} />
          <Route path="/incidents/:id" element={<Shell><IncidentDetail /></Shell>} />
          <Route path="/comms" element={<Shell><CommDetector /></Shell>} />
          <Route path="/voice" element={<Shell><VoiceVerification /></Shell>} />
          <Route path="/reports" element={<Shell><Reports /></Shell>} />
          <Route path="/audit" element={<Shell><AuditTrail /></Shell>} />
          <Route path="/settings" element={<Shell><Settings /></Shell>} />
          <Route path="/integrations" element={<Shell><Integrations /></Shell>} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
