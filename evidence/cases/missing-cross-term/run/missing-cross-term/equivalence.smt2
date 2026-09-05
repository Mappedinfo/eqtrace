; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () Real)
(assert
 (<= (- 2.0) x))
(assert
 (>= 2.0 x))
(assert
 (let ((?x32 (* x x)))
(let ((?x29 (+ ?x32 1.0)))
(let ((?x9 (^ (+ x 1.0) 2.0)))
(and (distinct ?x9 ?x29) true)))))
(check-sat)
