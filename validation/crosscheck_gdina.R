# Compare AlgebraDx estimates with the R package GDINA on the same data.
# install.packages(c("GDINA", "jsonlite")); then from the repository root:
#   Rscript validation/crosscheck_gdina.R
# Expected: log-likelihoods agree to ~0.01 and item probabilities to ~1e-3
# (both are ML estimates of the same model; tiny differences come from stopping rules).
suppressMessages({library(GDINA); library(jsonlite)})
dat <- as.matrix(read.csv("validation/crosscheck_data.csv"))
Q   <- as.matrix(read.csv("validation/crosscheck_q.csv"))
py  <- fromJSON("validation/crosscheck_algebradx.json", simplifyVector = FALSE)
for (m in c("GDINA", "DINA", "ACDM")) {
  fit <- GDINA(dat, Q, model = m, verbose = 0,
               control = list(conv.crit = 1e-7, maxitr = 5000))
  ll_r  <- as.numeric(logLik(fit))
  ll_py <- py[[m]]$loglik
  pr <- coef(fit, what = "itemprob")
  # AlgebraDx orders an item's latent groups as binary numbers with the item's first
  # attribute most significant (00, 01, 10, 11); GDINA labels them "P(10)" etc. in its own
  # order, so match groups by their attribute pattern.
  diffs <- mapply(function(r, p) {
    pats <- gsub("^P\\(|\\)$", "", names(r))
    Kj <- nchar(pats[1])
    idx <- sapply(pats, function(s) sum(as.integer(strsplit(s, "")[[1]]) * 2^((Kj - 1):0))) + 1
    max(abs(as.numeric(r) - unlist(p)[idx]))
  }, pr, py[[m]]$item_probs)
  cat(sprintf("%-6s loglik R %.3f  AlgebraDx %.3f  |diff| %.4f   max |item prob diff| %.5f\n",
              m, ll_r, ll_py, abs(ll_r - ll_py), max(diffs)))
}
