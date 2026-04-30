/**
 * physresidual_cli - portable command-line front-end for the physresidual C library.
 * Subcommands: power, measurement-l2, append-column, selftest, version, help
 */
#ifdef _MSC_VER
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif
#endif

#define PHYSRESIDUAL_CLI_VERSION "1.1.1"

#include "physresidual.h"

#include <ctype.h>
#include <errno.h>
#include <locale.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
#include <conio.h>
#include <fcntl.h>
#include <io.h>
#include <windows.h>
#include <limits.h>
#endif

enum { MAX_FILE_BYTES = 64 * 1024 * 1024 };

static void die(const char *msg)
{
    fprintf(stderr, "%s\n", msg);
    exit(1);
}

static void *xmalloc(size_t n)
{
    void *p = malloc(n);
    if (!p) {
        die("out of memory");
    }
    return p;
}

/* Remove UTF-8 BOM if present (in-place). */
static void strip_bom(char *s, size_t *len_io)
{
    size_t len = *len_io;
    if (len >= 3u && (unsigned char)s[0] == 0xEFu && (unsigned char)s[1] == 0xBBu && (unsigned char)s[2] == 0xBFu) {
        memmove(s, s + 3, len - 2u);
        len -= 3u;
        s[len] = '\0';
        *len_io = len;
    }
}

/* Drop full-line # comments; keep data lines (in-place shrink). */
static void strip_hash_comments(char *s)
{
    char *w = s;
    const char *r = s;
    while (*r) {
        const char *line_start = r;
        const char *nl = strchr(r, '\n');
        const char *line_end = nl ? nl + 1 : r + strlen(r);
        const char *p = line_start;
        while (p < line_end && (*p == ' ' || *p == '\t' || *p == '\r')) {
            ++p;
        }
        if (p < line_end && *p == '#') {
            r = line_end;
            continue;
        }
        while (r < line_end) {
            *w++ = *r++;
        }
    }
    *w = '\0';
}

static char *read_text_file(const char *path, size_t *out_len)
{
    FILE *f;
    if (path[0] == '-' && path[1] == '\0') {
        f = stdin;
#if defined(_WIN32)
        _setmode(_fileno(stdin), O_BINARY);
#endif
    } else {
        f = fopen(path, "rb");
        if (!f) {
            fprintf(stderr, "cannot open input: %s\n", path);
            exit(1);
        }
    }
    if (fseek(f, 0, SEEK_END) != 0) {
        if (f != stdin) {
            rewind(f);
        }
        size_t cap = 65536;
        size_t len = 0;
        char *buf = (char *)xmalloc(cap);
        for (;;) {
            size_t n = fread(buf + len, 1, cap - len - 1, f);
            len += n;
            if (n == 0) {
                break;
            }
            if (len + 1 >= cap) {
                cap *= 2;
                if (cap > (size_t)MAX_FILE_BYTES) {
                    die("input too large");
                }
                buf = (char *)realloc(buf, cap);
                if (!buf) {
                    die("out of memory");
                }
            }
        }
        buf[len] = '\0';
        if (f != stdin) {
            fclose(f);
        }
        strip_bom(buf, &len);
        strip_hash_comments(buf);
        *out_len = strlen(buf);
        return buf;
    }
    long sz = ftell(f);
    if (sz < 0 || sz > MAX_FILE_BYTES) {
        fclose(f);
        die("input too large or invalid");
    }
    rewind(f);
    char *buf = (char *)xmalloc((size_t)sz + 1u);
    if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) {
        fclose(f);
        free(buf);
        die("read error");
    }
    buf[sz] = '\0';
    if (f != stdin) {
        fclose(f);
    }
    size_t len = (size_t)sz;
    strip_bom(buf, &len);
    strip_hash_comments(buf);
    *out_len = strlen(buf);
    return buf;
}

/* Count numbers on first non-empty line (for --infer-cols). */
static size_t infer_cols_from_first_line(const char *text)
{
    const char *p = text;
    for (;;) {
        p += strspn(p, " \t\r\n");
        if (*p == '\0') {
            return 0;
        }
        if (*p == '#') {
            const char *nl = strchr(p, '\n');
            p = nl ? nl + 1 : p + strlen(p);
            continue;
        }
        break;
    }
    const char *q = p;
    const char *line_end = strpbrk(q, "\r\n");
    if (!line_end) {
        line_end = q + strlen(q);
    }
    size_t count = 0;
    while (q < line_end) {
        q += strspn(q, " \t,;");
        if (q >= line_end || *q == '\0') {
            break;
        }
        char *end = NULL;
        errno = 0;
        (void)strtod(q, &end);
        if (end == q || errno == ERANGE) {
            return 0;
        }
        ++count;
        q = end;
    }
    return count;
}

static size_t count_parse_doubles(const char *text, double **out_values)
{
    size_t cap = 1024;
    size_t n = 0;
    double *v = (double *)xmalloc(cap * sizeof(double));
    const char *p = text;
    for (;;) {
        p += strspn(p, " \t\r\n,;");
        if (*p == '\0') {
            break;
        }
        char *end = NULL;
        errno = 0;
        double x = strtod(p, &end);
        if (end == p || errno == ERANGE) {
            fprintf(stderr, "parse error near: %.40s\n", p);
            exit(1);
        }
        if (n >= cap) {
            cap *= 2;
            v = (double *)realloc(v, cap * sizeof(double));
            if (!v) {
                die("out of memory");
            }
        }
        v[n++] = x;
        p = end;
    }
    *out_values = v;
    return n;
}

static void write_doubles_csv(FILE *fp, const double *v, size_t n, int one_column)
{
    for (size_t i = 0; i < n; ++i) {
        fprintf(fp, "%.17g", v[i]);
        if (one_column) {
            fprintf(fp, "\n");
        } else {
            if (i + 1 < n) {
                fprintf(fp, ",");
            }
        }
    }
    if (!one_column && n > 0) {
        fprintf(fp, "\n");
    }
}

static FILE *open_out(const char *path)
{
    if (path[0] == '-' && path[1] == '\0') {
#if defined(_WIN32)
        _setmode(_fileno(stdout), O_BINARY);
#endif
        return stdout;
    }
    FILE *fp = fopen(path, "wb");
    if (!fp) {
        fprintf(stderr, "cannot open output: %s\n", path);
        exit(1);
    }
    return fp;
}

static void usage(FILE *fp)
{
    fprintf(fp,
            "physresidual_cli %s - CLI for physresidual (power-balance and measurement residuals)\n\n"
            "Usage:\n"
            "  physresidual_cli help | version | selftest\n"
            "  physresidual_cli power --in FILE [--cols B] [-o FILE] [--out FILE] [--abs]\n"
            "      Each sample is one row of B numbers. If --cols is omitted, B is inferred from the first data line.\n"
            "  physresidual_cli measurement-l2 --y FILE --hx FILE [--cols M] [-o FILE]\n"
            "  physresidual_cli append-column --matrix FILE --values FILE [--cols-in K] [-o FILE]\n"
            "      Matrix row-major n x K; values file must contain exactly n numbers.\n\n"
            "Lines starting with # are comments. UTF-8 BOM is skipped.\n"
            "Use - for stdin/stdout. Max input size %d MiB.\n",
            PHYSRESIDUAL_CLI_VERSION, MAX_FILE_BYTES / (1024 * 1024));
}

static int arg_eq(const char *a, const char *b)
{
    return strcmp(a, b) == 0;
}

static int file_exists(const char *path)
{
    FILE *fp = fopen(path, "rb");
    if (!fp) {
        return 0;
    }
    fclose(fp);
    return 1;
}

#if defined(_WIN32)
static void join_path(char *out, size_t out_cap, const char *a, const char *b)
{
    size_t la = strlen(a);
    int need_sep = (la > 0 && a[la - 1] != '\\' && a[la - 1] != '/');
    _snprintf_s(out, out_cap, _TRUNCATE, "%s%s%s", a, need_sep ? "\\" : "", b);
}

static int get_exe_dir(char *out, size_t out_cap)
{
    DWORD n = GetModuleFileNameA(NULL, out, (DWORD)out_cap);
    if (n == 0 || n >= out_cap) {
        return 0;
    }
    while (n > 0) {
        char c = out[n - 1];
        if (c == '\\' || c == '/') {
            out[n - 1] = '\0';
            return 1;
        }
        --n;
    }
    return 0;
}
#endif

static const char *get_opt(int argc, char **argv, int *i, const char *name)
{
    if (*i + 1 >= argc) {
        fprintf(stderr, "missing value for %s\n", name);
        exit(1);
    }
    (*i)++;
    return argv[*i];
}

static void pause_if_windows_console(void)
{
#if defined(_WIN32)
    if (GetConsoleWindow() != NULL) {
        fprintf(stdout, "\nPress any key to close...\n");
        fflush(stdout);
        (void)_getch();
    }
#endif
}

static void cmd_version(void)
{
    printf("physresidual_cli %s (physresidual library compatible)\n", PHYSRESIDUAL_CLI_VERSION);
}

static void cmd_help(void)
{
    usage(stdout);
}

static int selftest(void)
{
    const double powers[] = {10.0, -3.0, -7.0, 10.0, -3.0, -5.0};
    const size_t rows = 2;
    const size_t cols = 3;
    double r[2];
    phys_power_balance_residual(powers, rows, cols, r);
    if (fabs(r[0]) > 1e-12 || fabs(r[1] - 2.0) > 1e-12) {
        fprintf(stderr, "selftest FAIL: power_balance got %g %g expected 0 and 2\n", r[0], r[1]);
        return 1;
    }
    double y[] = {1.0, 0.0, 2.0, 0.0};
    double hx[] = {1.0, 0.1, 2.0, -0.1};
    double m[2];
    phys_measurement_residual_l2(y, hx, 2, 2, m);
    if (fabs(m[0] - 0.1) > 1e-9 || fabs(m[1] - 0.1) > 1e-9) {
        fprintf(stderr, "selftest FAIL: measurement_l2 got %g %g expected 0.1 0.1\n", m[0], m[1]);
        return 1;
    }
    double mat[] = {1.0, 2.0, 3.0, 4.0};
    double val[] = {5.0, 6.0};
    double out[6];
    phys_append_column(mat, val, 2, 2, out);
    if (out[0] != 1 || out[1] != 2 || out[2] != 5 || out[3] != 3 || out[4] != 4 || out[5] != 6) {
        fprintf(stderr, "selftest FAIL: append_column\n");
        return 1;
    }
    printf("selftest OK (power_balance, measurement_l2, append_column)\n");
    return 0;
}

static void cmd_power(int argc, char **argv)
{
    const char *in_path = NULL;
    const char *out_path = "-";
    size_t cols = 0;
    int abs_flag = 0;
    int cols_explicit = 0;
    for (int i = 2; i < argc; ++i) {
        if (arg_eq(argv[i], "--in")) {
            in_path = get_opt(argc, argv, &i, "--in");
        } else if (arg_eq(argv[i], "-o") || arg_eq(argv[i], "--out")) {
            out_path = get_opt(argc, argv, &i, argv[i]);
        } else if (arg_eq(argv[i], "--cols")) {
            cols = (size_t)strtoull(get_opt(argc, argv, &i, "--cols"), NULL, 10);
            cols_explicit = 1;
        } else if (arg_eq(argv[i], "--abs")) {
            abs_flag = 1;
        } else {
            fprintf(stderr, "unknown option: %s\n", argv[i]);
            exit(1);
        }
    }
    if (!in_path) {
        die("power: require --in FILE");
    }
    size_t text_len = 0;
    char *text = read_text_file(in_path, &text_len);
    (void)text_len;
    if (!cols_explicit) {
        size_t ic = infer_cols_from_first_line(text);
        if (ic == 0) {
            free(text);
            die("power: could not infer columns from first data line; pass --cols B explicitly");
        }
        cols = ic;
    } else if (cols == 0) {
        free(text);
        die("power: --cols must be at least 1");
    }
    double *vals = NULL;
    size_t total = count_parse_doubles(text, &vals);
    free(text);
    if (total == 0) {
        free(vals);
        die("power: no numeric data found in input");
    }
    if (cols == 0 || total % cols != 0) {
        fprintf(stderr,
                "power: value count %zu is not a multiple of columns %zu\n"
                "  hint: use --infer-cols or set --cols to match each row's field count\n",
                total, cols);
        free(vals);
        exit(1);
    }
    size_t rows = total / cols;
    double *res = (double *)xmalloc(rows * sizeof(double));
    phys_power_balance_residual(vals, rows, cols, res);
    free(vals);
    if (abs_flag) {
        for (size_t i = 0; i < rows; ++i) {
            res[i] = fabs(res[i]);
        }
    }
    FILE *fp = open_out(out_path);
    write_doubles_csv(fp, res, rows, 1);
    if (fp != stdout) {
        fclose(fp);
    }
    free(res);
}

static void cmd_measurement_l2(int argc, char **argv)
{
    const char *y_path = NULL;
    const char *hx_path = NULL;
    const char *out_path = "-";
    size_t cols = 0;
    int cols_explicit = 0;
    for (int i = 2; i < argc; ++i) {
        if (arg_eq(argv[i], "--y")) {
            y_path = get_opt(argc, argv, &i, "--y");
        } else if (arg_eq(argv[i], "--hx")) {
            hx_path = get_opt(argc, argv, &i, "--hx");
        } else if (arg_eq(argv[i], "-o") || arg_eq(argv[i], "--out")) {
            out_path = get_opt(argc, argv, &i, argv[i]);
        } else if (arg_eq(argv[i], "--cols")) {
            cols = (size_t)strtoull(get_opt(argc, argv, &i, "--cols"), NULL, 10);
            cols_explicit = 1;
        } else {
            fprintf(stderr, "unknown option: %s\n", argv[i]);
            exit(1);
        }
    }
    if (!y_path || !hx_path) {
        die("measurement-l2: require --y and --hx");
    }
    size_t leny = 0, lenh = 0;
    char *ty = read_text_file(y_path, &leny);
    char *th = read_text_file(hx_path, &lenh);
    (void)leny;
    (void)lenh;
    if (!cols_explicit) {
        size_t ic = infer_cols_from_first_line(ty);
        if (ic == 0) {
            free(ty);
            free(th);
            die("measurement-l2: could not infer --cols from --y first line; pass --cols M");
        }
        cols = ic;
    } else if (cols == 0) {
        free(ty);
        free(th);
        die("measurement-l2: --cols must be at least 1");
    }
    double *y = NULL, *hx = NULL;
    size_t ny = count_parse_doubles(ty, &y);
    size_t nh = count_parse_doubles(th, &hx);
    free(ty);
    free(th);
    if (ny != nh) {
        fprintf(stderr, "y and hx length mismatch: %zu vs %zu\n", ny, nh);
        free(y);
        free(hx);
        exit(1);
    }
    if (ny == 0 || ny % cols != 0) {
        fprintf(stderr, "measurement-l2: length %zu not divisible by cols %zu\n", ny, cols);
        free(y);
        free(hx);
        exit(1);
    }
    size_t rows = ny / cols;
    double *res = (double *)xmalloc(rows * sizeof(double));
    phys_measurement_residual_l2(y, hx, rows, cols, res);
    free(y);
    free(hx);
    FILE *fp = open_out(out_path);
    write_doubles_csv(fp, res, rows, 1);
    if (fp != stdout) {
        fclose(fp);
    }
    free(res);
}

static void cmd_append_column(int argc, char **argv)
{
    const char *m_path = NULL;
    const char *v_path = NULL;
    const char *out_path = "-";
    size_t cols_in = 0;
    int cols_explicit = 0;
    for (int i = 2; i < argc; ++i) {
        if (arg_eq(argv[i], "--matrix")) {
            m_path = get_opt(argc, argv, &i, "--matrix");
        } else if (arg_eq(argv[i], "--values")) {
            v_path = get_opt(argc, argv, &i, "--values");
        } else if (arg_eq(argv[i], "-o") || arg_eq(argv[i], "--out")) {
            out_path = get_opt(argc, argv, &i, argv[i]);
        } else if (arg_eq(argv[i], "--cols-in")) {
            cols_in = (size_t)strtoull(get_opt(argc, argv, &i, "--cols-in"), NULL, 10);
            cols_explicit = 1;
        } else {
            fprintf(stderr, "unknown option: %s\n", argv[i]);
            exit(1);
        }
    }
    if (!m_path || !v_path) {
        die("append-column: require --matrix and --values");
    }
    size_t lm = 0, lv = 0;
    char *tm = read_text_file(m_path, &lm);
    char *tv = read_text_file(v_path, &lv);
    (void)lm;
    (void)lv;
    if (!cols_explicit) {
        size_t ic = infer_cols_from_first_line(tm);
        if (ic == 0) {
            free(tm);
            free(tv);
            die("append-column: could not infer --cols-in from matrix first line; pass --cols-in K");
        }
        cols_in = ic;
    } else if (cols_in == 0) {
        free(tm);
        free(tv);
        die("append-column: --cols-in must be at least 1");
    }
    double *mat = NULL, *vals = NULL;
    size_t nm = count_parse_doubles(tm, &mat);
    size_t nv = count_parse_doubles(tv, &vals);
    free(tm);
    free(tv);
    if (nm == 0 || nm % cols_in != 0) {
        fprintf(stderr, "matrix element count %zu not divisible by cols-in %zu\n", nm, cols_in);
        free(mat);
        free(vals);
        exit(1);
    }
    size_t rows = nm / cols_in;
    if (nv != rows) {
        fprintf(stderr, "values count %zu must equal matrix row count %zu\n", nv, rows);
        free(mat);
        free(vals);
        exit(1);
    }
    size_t out_cols = cols_in + 1u;
    double *out = (double *)xmalloc(rows * out_cols * sizeof(double));
    phys_append_column(mat, vals, rows, cols_in, out);
    free(mat);
    free(vals);
    FILE *fp = open_out(out_path);
    for (size_t i = 0; i < rows; ++i) {
        for (size_t j = 0; j < out_cols; ++j) {
            fprintf(fp, "%.17g", out[i * out_cols + j]);
            if (j + 1 < out_cols) {
                fprintf(fp, ",");
            }
        }
        fprintf(fp, "\n");
    }
    if (fp != stdout) {
        fclose(fp);
    }
    free(out);
}

int main(int argc, char **argv)
{
    (void)setlocale(LC_ALL, "C");

    if (argc < 2) {
        const char *sample_rel = "examples\\sample_powers.csv";
        char sample_path[4096];
        sample_path[0] = '\0';
        fprintf(stdout, "No command provided. Running built-in diagnostics...\n\n");
        if (selftest() != 0) {
            fprintf(stdout, "\nSelf-test failed.\n");
            pause_if_windows_console();
            return 1;
        }
#if defined(_WIN32)
        {
            char exe_dir[4096];
            char parent_dir[4096];
            if (get_exe_dir(exe_dir, sizeof(exe_dir))) {
                strncpy_s(parent_dir, sizeof(parent_dir), exe_dir, _TRUNCATE);
                char *last_sep = strrchr(parent_dir, '\\');
                if (!last_sep) {
                    last_sep = strrchr(parent_dir, '/');
                }
                if (last_sep) {
                    *last_sep = '\0'; /* parent of dist */
                    join_path(sample_path, sizeof(sample_path), parent_dir, sample_rel);
                }
            }
        }
#endif
        if (sample_path[0] != '\0' && file_exists(sample_path)) {
            char *demo_argv[] = { argv[0], "power", "--in", sample_path, "-o", "-", NULL };
            fprintf(stdout, "\nDemo run on %s:\n", sample_path);
            cmd_power(6, demo_argv);
        } else if (file_exists(sample_rel)) {
            char *demo_argv[] = { argv[0], "power", "--in", (char *)sample_rel, "-o", "-", NULL };
            fprintf(stdout, "\nDemo run on %s:\n", sample_rel);
            cmd_power(6, demo_argv);
        } else {
            fprintf(stdout, "\nSample file not found (%s), skipping demo.\n", sample_rel);
        }
        fprintf(stdout, "\nQuick usage:\n");
        fprintf(stdout, "  %s selftest\n", argv[0]);
        fprintf(stdout, "  %s power --in examples\\sample_powers.csv -o -\n", argv[0]);
        fprintf(stdout, "  %s measurement-l2 --y y.csv --hx hx.csv --cols 2 -o out.txt\n", argv[0]);
        fprintf(stdout, "Tip: drag-and-drop a data file onto this .exe to run power mode automatically.\n");
        pause_if_windows_console();
        return 0;
    }
    if (argc == 2 && file_exists(argv[1])) {
        char *auto_argv[] = { argv[0], "power", "--in", argv[1], "-o", "-", NULL };
        cmd_power(6, auto_argv);
        return 0;
    }
    if (arg_eq(argv[1], "help") || arg_eq(argv[1], "-h") || arg_eq(argv[1], "--help")) {
        cmd_help();
        return 0;
    }
    if (arg_eq(argv[1], "version") || arg_eq(argv[1], "--version")) {
        cmd_version();
        return 0;
    }
    if (arg_eq(argv[1], "selftest")) {
        return selftest();
    }
    if (arg_eq(argv[1], "power")) {
        cmd_power(argc, argv);
        return 0;
    }
    if (arg_eq(argv[1], "measurement-l2")) {
        cmd_measurement_l2(argc, argv);
        return 0;
    }
    if (arg_eq(argv[1], "append-column")) {
        cmd_append_column(argc, argv);
        return 0;
    }
    fprintf(stderr, "unknown command: %s\n", argv[1]);
    usage(stdout);
    return 1;
}
