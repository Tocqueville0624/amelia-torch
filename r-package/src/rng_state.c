#include <R.h>
#include <Rinternals.h>
#include <R_ext/Random.h>
#include <R_ext/Rdynload.h>
#include <R_ext/Visibility.h>

/* Amelia 1.8.3's C++ imputer advances R's C-level RNG without PutRNGstate.
 * A subsequent reticulate RNGScope would otherwise reload a stale .Random.seed.
 * Keep both states independently; these functions never draw random numbers. */
static SEXP rng_snapshot(void) {
    SEXP seed_symbol = Rf_install(".Random.seed");
    SEXP visible = Rf_findVarInFrame(R_GlobalEnv, seed_symbol);
    int had_seed = visible != R_UnboundValue;
    SEXP result = PROTECT(Rf_allocVector(VECSXP, 3));
    SET_VECTOR_ELT(result, 0, Rf_ScalarLogical(had_seed));
    SET_VECTOR_ELT(result, 1, had_seed ? Rf_duplicate(visible) : R_NilValue);
    /* Initialize a valid stream only if the session has never had an R seed. */
    if (!had_seed) GetRNGstate();
    PutRNGstate();
    SET_VECTOR_ELT(result, 2,
                   Rf_duplicate(Rf_findVarInFrame(R_GlobalEnv, seed_symbol)));
    UNPROTECT(1);
    return result;
}

static SEXP rng_restore(SEXP snapshot) {
    if (TYPEOF(snapshot) != VECSXP || XLENGTH(snapshot) != 3 ||
        TYPEOF(VECTOR_ELT(snapshot, 0)) != LGLSXP ||
        XLENGTH(VECTOR_ELT(snapshot, 0)) != 1 ||
        TYPEOF(VECTOR_ELT(snapshot, 2)) != INTSXP) {
        Rf_error("Invalid internal RNG snapshot");
    }
    SEXP seed_symbol = Rf_install(".Random.seed");
    Rf_defineVar(seed_symbol, VECTOR_ELT(snapshot, 2), R_GlobalEnv);
    GetRNGstate();
    if (LOGICAL(VECTOR_ELT(snapshot, 0))[0]) {
        Rf_defineVar(seed_symbol, VECTOR_ELT(snapshot, 1), R_GlobalEnv);
    } else {
        R_removeVarFromFrame(seed_symbol, R_GlobalEnv);
    }
    return R_NilValue;
}

static const R_CallMethodDef call_methods[] = {
    {"C_amelia_rng_snapshot", (DL_FUNC) &rng_snapshot, 0},
    {"C_amelia_rng_restore", (DL_FUNC) &rng_restore, 1},
    {NULL, NULL, 0}
};

void attribute_visible R_init_ameliatorch(DllInfo *dll) {
    R_registerRoutines(dll, NULL, call_methods, NULL, NULL);
    R_useDynamicSymbols(dll, FALSE);
    R_forceSymbols(dll, TRUE);
}
