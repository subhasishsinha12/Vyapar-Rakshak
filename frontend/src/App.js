import React from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";

import { AuthProvider } from "./lib/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";

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
import CommDetector from "./pages/CommDetector";
import VoiceVerification from "./pages/VoiceVerification";

function Shell({ children }) {
  return (
    <ProtectedRoute>
      <Layout>{children}</Layout>
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
          <Route path="/" element={<Shell><Dashboard /></Shell>} />
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
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
