export type Job = {
  id: string;
  role: string;
  company: string;
  logo: string;
  location: string;
  type: string;
  match: number;
  skills: string[];
  desc: string;
  requirements: string[];
};

export type Application = {
  id: string;
  company: string;
  role: string;
  date: string;
  status: "Applied" | "Under Review" | "Verification" | "Interview" | "Decision";
  match: number;
};

export type VerificationStatus = "Not Verified" | "Pending" | "Verified" | "Needs attention" | "Failed";

export type Verification = {
  id: string;
  title: string;
  status: VerificationStatus;
  summary: string;
  proofId: string;
  facts: string[];
};

export const jobs: Job[] = [
  {
    id: "backend-engineer",
    role: "Backend Engineer",
    company: "Acme Technologies",
    logo: "A",
    location: "Remote",
    type: "Full-time",
    match: 94,
    skills: ["Python ≥ 3 years", "PostgreSQL", "AWS"],
    desc: "We're building infrastructure that helps modern teams move faster without compromising reliability.",
    requirements: [
      "Python with 3+ years of professional experience",
      "PostgreSQL and data modeling experience",
      "Experience deploying services on AWS",
      "Strong collaboration across product and platform teams",
    ],
  },
  {
    id: "ml-engineer",
    role: "Machine Learning Engineer",
    company: "TechCorp",
    logo: "T",
    location: "Tokyo, JP",
    type: "Hybrid",
    match: 91,
    skills: ["Python", "PyTorch", "MLOps"],
    desc: "Join our applied AI team to turn research into reliable products used by thousands of customers.",
    requirements: [
      "Experience training and evaluating ML models",
      "Production MLOps workflows",
      "Python and model deployment experience",
      "Ability to work across research and product teams",
    ],
  },
  {
    id: "python-engineer",
    role: "Python Engineer",
    company: "DataLabs",
    logo: "D",
    location: "Remote",
    type: "Full-time",
    match: 88,
    skills: ["Python", "FastAPI", "Docker"],
    desc: "Help us develop fast, elegant data services for analytics teams around the world.",
    requirements: [
      "Python service development",
      "FastAPI and Docker experience",
      "Reliable API design and testing",
      "Cross-functional engineering communication",
    ],
  },
  {
    id: "frontend-engineer",
    role: "Frontend Engineer",
    company: "Northstar",
    logo: "N",
    location: "Singapore",
    type: "Remote",
    match: 84,
    skills: ["JavaScript", "React", "CSS"],
    desc: "Create polished product experiences that make complex workflows feel beautifully simple.",
    requirements: [
      "Strong JavaScript and React experience",
      "Design systems and product UX thinking",
      "CSS and accessibility awareness",
      "Product-minded collaboration",
    ],
  },
];

export const applications: Application[] = [
  {
    id: "app-001",
    company: "Acme Technologies",
    role: "Backend Engineer",
    date: "Aug 24",
    status: "Verification",
    match: 94,
  },
  {
    id: "app-002",
    company: "TechCorp",
    role: "Machine Learning Engineer",
    date: "Aug 21",
    status: "Under Review",
    match: 91,
  },
  {
    id: "app-003",
    company: "DataLabs",
    role: "Python Engineer",
    date: "Aug 17",
    status: "Interview",
    match: 88,
  },
];

export const verifications: Verification[] = [
  {
    id: "vig-001",
    title: "Python and backend engineering",
    status: "Verified",
    summary: "Professional Python experience and backend delivery requirements satisfied.",
    proofId: "VH-7A92-X31",
    facts: ["Python ≥ 3 years", "Backend systems", "Production deployment"],
  },
  {
    id: "vig-002",
    title: "AWS deployment credential",
    status: "Pending",
    summary: "Employer requested a final review of cloud deployment evidence.",
    proofId: "VH-9F12-Q66",
    facts: ["AWS deployment", "CI/CD workflow", "Infrastructure support"],
  },
  {
    id: "vig-003",
    title: "PostgreSQL expertise",
    status: "Needs attention",
    summary: "Additional schema and optimization evidence may be required.",
    proofId: "VH-3C44-A81",
    facts: ["Schema design", "Query optimization", "Database migrations"],
  },
];

export const candidateProfile = {
  name: "Trina Smith",
  headline: "Backend Engineer",
  skills: ["Python", "PostgreSQL", "AWS", "System Design"],
  identityVerified: true,
  privacyLevel: "Private by default",
};

export const employerCandidates = [
  { id: "vh-104", match: 96, role: "Backend Engineer", status: "Verified" },
  { id: "vh-219", match: 91, role: "Backend Engineer", status: "Verified" },
  { id: "vh-307", match: 87, role: "Machine Learning Engineer", status: "Pending" },
];

export const navItems = {
  candidate: [
    { key: "overview", href: "/dashboard", label: "Overview" },
    { key: "jobs", href: "/jobs", label: "Jobs" },
    { key: "applications", href: "/applications", label: "Applications" },
    { key: "verify", href: "/verify", label: "Verifications" },
    { key: "profile", href: "/profile", label: "Profile" },
    { key: "settings", href: "/settings", label: "Settings" },
  ],
  employer: [
    { key: "employer", href: "/employer", label: "Overview" },
    { key: "jobs", href: "/employer/jobs", label: "Job listings" },
    { key: "candidates", href: "/employer/candidates", label: "Candidates" },
    { key: "settings", href: "/settings", label: "Settings" },
  ],
};
