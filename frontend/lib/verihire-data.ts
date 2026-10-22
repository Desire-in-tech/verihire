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

export const candidateProfile = {
  name: "Trina Smith",
  headline: "Backend Engineer",
  skills: ["Python", "PostgreSQL", "AWS", "System Design"],
  privacyLevel: "Private by default",
};

export type CVUploadResult = {
  upload_id: string;
  matching_results: Array<{
    job_id: string;
    matches: boolean;
    score: number;
  }>;
  proof_results: Array<{
    job_id: string;
    applicant_verified: boolean;
    proof_data?: {
      message?: string;
      verification_status?: "verified" | "failed" | "unavailable" | "not_configured" | "unknown" | null;
      eligible?: boolean | null;
      unsupported_criteria?: string[];
      proof_id?: string | null;
      block_height?: number | null;
    };
  }>;
};

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
