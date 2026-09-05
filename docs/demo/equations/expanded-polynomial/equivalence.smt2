; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () Real)
(assert
 (<= (- 4.0) x))
(assert
 (>= 4.0 x))
(assert
 (let ((?x26 (+ (+ (* x x) (* 2.0 x)) 1.0)))
(let ((?x23 (^ (+ x 1.0) 2.0)))
(and (distinct ?x23 ?x26) true))))
(check-sat)
